#imports
import logging
from fnx import date
from openerp.exceptions import ERPError
from osv import osv, fields
from VSS.finance import FederalHoliday

_logger = logging.getLogger(__name__)

#tables
class hr_workers_comp_claim(osv.Model):
    "workers comp information fields"
    _name = 'hr.workers_comp.claim'

    def _construct_initial_note(self, cr, uid, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        duty_id = ir_model_data.get_object_reference(cr, uid, 'hr_workers_comp', 'duty_none')[1]
        today = fields.date.context_today(self, cr, uid, context=context)
        return [[0, False, {'duty_id': duty_id, 'effective_date': today}]]

    def _total_days(self, cr, uid, ids, field_names=None, arg=None, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = self.onchange_dates(cr, uid, rec.id, rec.injury_date, rec.notes_ids, context=context)['value']
        return res

    _columns = {
        'state': fields.selection(
            [('open', 'Open'), ('closed', 'Closed')],
            'Status',
            sort_order='definition',
            ),
        'restriction_state': fields.selection(
            [('full', 'Full Restriction'), ('light', 'Light Duty'), ('none', 'None')],
            'Duty',
            sort_order='definition',
            ),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'notification_date': fields.date('Notified on', help='Date employee notified us of injury'),
        'injury_ids': fields.many2many(
            'hr.workers_comp.injury',
            'claim2injury_rel', 'claim_id', 'injury_id',
            string='Injury',
            ),
        'injury_date': fields.date('Injury Date'),
        'location_id': fields.many2one('hr.department', 'Accident Location'),
        'notes': fields.text('Notes'),
        'notes_ids': fields.one2many('hr.workers_comp.history', 'claim_id', 'Notes'),
        'state_claim_id': fields.char('State Claim Number', size=64),
        'attorney': fields.boolean('Attorney', help='Has employee retained a lawyer?'),
        'reserved_amount': fields.float('Reserved Funds', help='Amount set aside to pay this claim.'),
        'paid_amount': fields.float('Paid Funds', help='Amount paid to employee so far.'),
        'full_duty_lost': fields.function(
            _total_days,
            type='integer',
            string='Full days lost',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['injury_date', 'full_duty'],
                    10,
                    ),
                },
            help='Full restriction = 1 day lost\nPartial restriction = 0.5 days lost',
            ),
        'restricted_duty_total': fields.function(
            _total_days,
            type='integer',
            string='Partial restriction days',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['injury_date', 'restricted_duty_start', 'restricted_duty_end'],
                    10,
                    ),
                },
            help='Number of days of light work.',
            ),
        'no_duty_total': fields.function(
            _total_days,
            type='integer',
            string='Full restriction days',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['injury_date', 'notes_ids'],
                    10,
                    ),
                },
            help='Number of days of no work',
            ),
        }

    _defaults = {
        'state': 'open',
        'restriction_state': 'full',
        'injury_date': fields.date.context_today,
        'notes_ids': _construct_initial_note,
        }

    def onchange_dates(self, cr, uid, ids, injury_date, notes_ids, context=None):
        res = {}
        res['value'] = value = {}
        today = date(fields.date.context_today(self, cr, uid, context=context))
        injury_date = date(injury_date)
        lost = 0
        full_lost = 0
        partial_lost = 0
        if not injury_date:
            return {'value': {
                        'full_duty_lost': 0,
                        'restricted_duty_total': 0,
                        'no_duty_total': 0,
                        }}
        note_history = self.pool.get('hr.workers_comp.history')
        duty_type = self.pool.get('hr.workers_comp.duty_type')
        duty = dict([(r['id'], r['restriction']) for r in duty_type.read(cr, uid, context=context)])
        if not notes_ids:
            notes = [('Full', today)]
        else:
            if isinstance(notes_ids[0], list):
                # from web form
                notes = []
                for note in notes_ids:
                    if note[0] == 0:
                        # create
                        # [[0, False, {'note': False, 'effective_date': '2017-02-02', 'duty_id': 22}]]
                        notes.append((duty[note[2]['duty_id']], date(note[2]['effective_date'])))
                    elif note[0] == 1:
                        # update (so read old record and apply updates)
                        # [1, 15, {'effective_date': '2017-01-17'}]
                        note_update = note[2]
                        note = note_history.browse(cr, uid, note[1], context=context)
                        duty_id = note_update.get('duty_id')
                        if duty_id is None:
                            restriction = note.duty_id.restriction
                        else:
                            restriction = duty[duty_id]
                        eff_date = date(note_update.get('effective_date'))
                        if not eff_date:
                            eff_date = date(note.effective_date)
                        if restriction is None or eff_date is False:
                            # no recorded restriction and/or date, nothing we can calculate with this record
                            continue
                        notes.append((restriction, eff_date))
                    elif note[0] in (2, 3, 5):
                        # various flavors of unlink
                        pass
                    elif note[0] == 4:
                        # link
                        # [[4, 10, False]]
                        note = note_history.browse(cr, uid, note[1], context=context)
                        notes.append((note.duty_id.restriction, date(note.effective_date)))
            else:
                # from function field
                # [note1, note2, note3, ...]
                notes = [(note.duty_id.restriction, note.effective_date) for note in notes_ids]
            notes.append((None, today))
        # ensure date sortation
        notes.sort(key=lambda p: p[1])
        # remove any items that take effect after today
        restriction = 'full'
        last_date = injury_date
        while notes[-1][1] > today:
            notes.pop()
        for restriction_level, eff_date in notes:
            # duty_state = duty_state.lower()
            if restriction_level is None:
                # fix entry for today
                restriction_level = restriction
            # calculate number of days in last state
            if restriction_level in ('none', 'na'):
                # unless those were no-restriction days
                restriction = restriction_level
                continue
            days = FederalHoliday.count_business_days(last_date, eff_date)
            if restriction == 'full':
                lost += days
                full_lost += days
            elif restriction == 'light':
                lost += 0.5 * days
                partial_lost += days
            else:
                raise ERPError('Bug!', 'unknown restriction state: %r' % restriction_level)
            restriction = restriction_level
            last_date = eff_date

        value['full_duty_lost'] = lost + 0.5  # round up
        value['restricted_duty_total'] = partial_lost
        value['no_duty_total'] = full_lost
        return res

    def recalc_days(self, cr, uid, *args):
        """
        recalculate lost and restricted days
        """
        # get open claims
        ids = self.search(cr, uid, [('state','=','open')])
        res = self._total_days(cr, uid, ids)
        for id, totals in res.items():
            self.write(cr, uid, id, totals)
        return True

    def button_hr_workers_comp_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'closed'}, context=context)

    def button_hr_workers_comp_reopen(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)


class hr_workers_comp_injury(osv.Model):
    "workers comp injury type"
    _name = 'hr.workers_comp.injury'
    _desc = "workers comp injury"

    _columns = {
        'name': fields.char('Description', size=128),
        }

    _sql_constraints = [
            ('injury_uniq', 'unique(name)', 'This injury already exists.'),
            ]

class hr_workers_comp_duty_type(osv.Model):
    "workers comp duty type"
    _name = 'hr.workers_comp.duty_type'
    _desc = "workers comp claim duty type"

    _columns = {
        'name': fields.char('Description', size=128),
        'restriction': fields.selection((
            ('full', 'No duties'),
            ('light', 'Light Duties'),
            ('none', 'Normal duties'),
            ('na', 'N/A'),
            ),
            string='Restriction level',
            help='No Duties -> Full restriction, no work\n'
                 'Light Duties -> light duties\n'
                 'Normal Duties -> No restrictions, normal work\n'
                 'N/A -> No longer employed',
            ),
        }

    _sql_constraints = [
            ('duty_uniq', 'unique(name)', 'This duty already exists.'),
            ]


class hr_workers_comp_history(osv.Model):
    "workers comp  history"
    _name = 'hr.workers_comp.history'
    _desc = "workers comp claim history entry"

    _columns = {
        'claim_id': fields.many2one('hr.workers_comp.claim', 'Claim #'),
        'create_date': fields.date('Date note entered', readonly=True),
        'write_uid': fields.many2one('res.users', 'Entered by'),
        'effective_date': fields.date('Effective Date', help='date this change takes effect'),
        'note': fields.text('Note'),
        'duty_id': fields.many2one('hr.workers_comp.duty_type', 'Duty Level'),
        }

    _defaults = {
        'effective_date': fields.date.context_today,
        }

class workers_comp_hr(osv.Model):
    "add link from hr.employee to hr_workers_comp_claim"
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    _columns = {
        'worker_comp_claim_ids': fields.one2many(
            'hr.workers_comp.claim', 'employee_id',
            string='Workers Compensation Claims',
            )
        }
