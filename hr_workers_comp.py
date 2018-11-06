#imports
from __future__ import print_function
import logging
from aenum import NamedTuple
from datetime import timedelta
from fnx import date
from openerp.exceptions import ERPError
from osv import osv, fields

_logger = logging.getLogger(__name__)

ONE_DAY = timedelta(1)

#tables
class hr_workers_comp_claim(osv.Model):
    "workers comp information fields"
    _name = 'hr.workers_comp.claim'

    def _construct_initial_note(self, cr, uid, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        duty_id = ir_model_data.get_object_reference(cr, uid, 'hr_workers_comp', 'duty_full')[1]
        today = fields.date.context_today(self, cr, uid, context=context)
        return [[0, False, {'duty_id': duty_id, 'evaluation_date': today}]]

    def _get_claim_ids(hr_workers_comp_history, cr, uid, ids, context=None):
        records = hr_workers_comp_history.read(cr, uid, ids, fields=['claim_id'], context=context)
        claim_ids = []
        for rec in records:
            claim = rec['claim_id']
            if claim:
                claim_ids.append(claim[0])
        return claim_ids

    def _total_days(self, cr, uid, ids, field_names=None, arg=None, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = self.onchange_dates(cr, uid, rec.id, rec.injury_date, rec.notes_ids, rec.state, context=context)['value']
        return res

    _columns = {
        'state': fields.selection(
            [('open', 'Open'), ('closed', 'Closed')],
            'Status',
            sort_order='definition',
            ),
        'restriction_state_id': fields.many2one('hr.workers_comp.duty_type', 'Duty'),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='restrict'),
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
        'total_days': fields.function(
            _total_days,
            fnct_inv=True,
            type='integer',
            string='Total days',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            help='Restricted days + days away from work',
            oldname='full_duty_lost',
            ),
        'total_days_300': fields.function(
            _total_days,
            fnct_inv=True,
            type='integer',
            string='Total days 300',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            help='Restricted days + days away from work',
            ),
        'restricted_duty_total': fields.function(
            _total_days,
            fnct_inv=True,
            type='integer',
            string='Restricted duties/job transfer days',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            help='Number of days of restricted duties.',
            ),
        'restricted_duty_total_300': fields.function(
            _total_days,
            fnct_inv=True,
            type='integer',
            string='Restricted duties/job transfer days 300',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            help='Number of days of restricted duties.',
            ),
        'no_duty_total': fields.function(
            _total_days,
            fnct_inv=True,
            type='integer',
            string='Days away from work',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            help='Number of days of no work',
            ),
        'no_duty_total_300': fields.function(
            _total_days,
            fnct_inv=True,
            type='integer',
            string='Days away from work 300',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            help='Number of days of no work',
            ),
        'days_by_year': fields.function(
            _total_days,
            fnct_inv=True,
            type='html',
            string='Summary',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['notes_ids'],
                    10,
                    ),
                'hr.workers_comp.history': (
                    _get_claim_ids,
                    ['evaluation_date', 'duty_id'],
                    15,
                    ),
                },
            ),
        }

    _defaults = {
        'state': 'open',
        }

    def write(self, cr, uid, ids, values, context=None):
        if 'notes_ids' in values:
            values['notes_ids'] = [t for t in values['notes_ids'] if t[0] != 4]
        return super(hr_workers_comp_claim, self).write(cr, uid, ids, values, context=context)

    def onchange_dates(self, cr, uid, ids, injury, notes_ids, claim_state, context=None):
        # also called by nightly update routine
        incomplete = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_workers_comp', 'incomplete')
        res = {}
        res['value'] = value = {}
        value.update({
                    'total_days': 0,
                    'restricted_duty_total': 0,
                    'no_duty_total': 0,
                    'total_days_300': 0,
                    'restricted_duty_total_300': 0,
                    'no_duty_total_300': 0,
                    'restriction_state_id': incomplete.id,
                    'days_by_year': ''
                    })
        if not notes_ids:
            return res
        # helper functions
        def _sort_notes(notes_ids, estimate=False):
            def _keep_record(restriction, eval_date):
                if restriction in ('na', False):
                    return False
                if estimate and restriction == 'est':
                    return True
                elif estimate and eval_date.year == injury_date.year:
                    return True
                elif not estimate and restriction != 'est':
                    return True
                else:
                    return False
            notes = []
            if isinstance(notes_ids[0], list):
                # from web form
                for note in notes_ids:
                    if note[0] == 0:
                        # create
                        # [0, False, {'note': False, 'evaluation_date': '2017-02-02', 'duty_id': 22, 'restriction': 'est'}]
                        try:
                            restriction = note[2]['restriction']
                            if restriction in ('na', False):
                                continue
                            duty_id = note[2].get('duty_id')
                            duty = duty_restrictions[duty_id]
                            eval_date = date(note[2]['evaluation_date'])
                            if _keep_record(restriction, eval_date):
                                notes.append(Note(restriction, eval_date, duty))
                        except Exception:
                            _logger.exception('bad note: %r', note)
                            raise
                    elif note[0] == 1:
                        # update (so read old record and apply updates)
                        # [1, 15, {'evaluation_date': '2017-01-17', 'duty_id': 13, 'restriction': 'full'}]
                        #
                        # new style note or old style?
                        note_update = note[2]
                        note = note_history.browse(cr, uid, note[1], context=context)
                        restriction = note_update.get('restriction') or note.restriction
                        if not restriction:
                            # old style: restriction is in duty_id -- abort calculations
                            raise OldStyleRestriction(note)
                        elif restriction in ('na', False):
                            continue
                        duty_id = note_update.get('duty_id')
                        if duty_id is None:
                            duty_id = note.duty_id
                        else:
                            duty_id = duty_restrictions[duty_id]
                        eval_date = date(note_update.get('evaluation_date'))
                        if not eval_date:
                            eval_date = date(note.evaluation_date)
                        if eval_date is False:
                            # no recorded restriction and/or date, nothing we can calculate with this record
                            # note: this shouldn't happen
                            raise InvalidNote(note)
                        if _keep_record(restriction, eval_date):
                            notes.append(Note(restriction, eval_date, duty_id))
                    elif note[0] in (2, 3, 5):
                        # various flavors of unlink
                        pass
                    elif note[0] == 4:
                        # link
                        # [[4, 10, False]]
                        note = note_history.browse(cr, uid, note[1], context=context)
                        restriction = note.restriction
                        if restriction in ('na', False):
                            continue
                        eval_date = date(note.evaluation_date)
                        if _keep_record(restriction, eval_date):
                            notes.append(Note(note.restriction, eval_date, note.duty_id))
            else:
                # from function field
                # [note1, note2, note3, ...]
                notes = []
                for note in notes_ids:
                    restriction = note.restriction
                    eval_date = date(note.evaluation_date)
                    if _keep_record(restriction, eval_date):
                        notes.append(Note(restriction, eval_date, note.duty_id))
            notes.sort(key=lambda n: n.date)
            return notes
        #
        def _calc_notes(notes, estimate=False):
            print('calculating %s notes' % (('normal', 'estimate')[estimate],))
            years = {}
            restricted = DayCounter()
            no_duty = DayCounter()
            last_note = notes[-1]
            today_added = False
            # check if last entry is earlier than today
            if last_note.date < today:
                if estimate and today.year != injury_date.year:
                    estimate_year = injury_date.replace(month=1, day=1, delta_year=1).year
                    years['%s estimate' % estimate_year] = YearCounter(estimate_year, estimate=True)
                elif last_note.restriction != 'none':
                    notes.append(Note(no_duty_restriction, today, None))
                    today_added = True
            # now add entries at year endings to help with yearly calculations
            # [('full', 2017-10-15, 'restriction'), ('none', 2018-03-15, 'cleared')]
            # becomes
            # [('full', 2017-10-15, 'restriction'), ('full', 2017-12-31, 'restriction'), ('none', 2018-03-15, 'cleared')]
            old_notes = notes
            notes = []
            last_restriction, last_date, last_duty = old_notes[0]
            notes.append(old_notes[0])
            for note in old_notes[1:]:
                if last_date.year < note.date.year:
                    # switched years, add final year entry
                    notes.append(Note(last_restriction, date(last_date.year, 12, 31), last_duty))
                notes.append(note)
                last_restriction, last_date, last_duty = note
            # prep for scans, and check if estimate needed
            last_restriction, last_date, last_duty = notes[0]
            years[str(last_date.year)] = YearCounter(last_date.year)
            for note in notes[1:]:
                print('note:', note)
                last_duty = note.duty_id
                # calculate number of days in last state
                if last_restriction == 'none':
                    # unless those were no-restriction days
                    last_restriction = note.restriction
                    last_date = note.date
                    continue
                days = note.date - last_date - ONE_DAY
                if last_restriction in ('light', 'full') and note.restriction in ('light', 'full'):
                    days += ONE_DAY
                # if processing an estimate batch, only one additional year will be present, so
                # set it up as an estimate year
                target_year = years.setdefault(
                        str(note.date.year) + ('', ' estimate')[estimate and note.date.year != injury_date.year],
                        YearCounter(note.date.year, estimate=estimate),
                        )
                if last_restriction == 'full':
                    target_year.full += days
                    no_duty += days
                elif last_restriction == 'light':
                    target_year.partial += days
                    restricted += days
                else:
                    raise ERPError('Bug!', 'unknown restriction state: %r' % last_restriction)
                print('duty_id:', note.duty_id)
                if note.restriction != 'est':
                    last_restriction = note.restriction
                else:
                    print('\nnote.restriction:', note.restriction)
                    print('note.duty_id:', note.duty_id.id, note.duty_id.name, '\n')
                    if note.duty_id.id == est_light_duty.id:
                        last_restriction = 'light'
                    elif note.duty_id.id == est_cleared.id:
                        last_restriction = 'none'
                    else:
                        raise Exception('bad duty_id: %s' % (note.duty_id, ))
                last_date = note.date
            if today_added:
                last_duty = notes[-2].duty_id
            print('\nyears:', years, '\nno duty:', no_duty, '\nrestricted:', restricted, '\n')
            return years, restricted, no_duty, last_duty
        #
        # main function
        #
        # establish values
        injury_date = date(injury)
        today = date(fields.date.context_today(self, cr, uid, context=context))
        no_duty_restriction = 'none'
        ir_model_data = self.pool.get('ir.model.data')
        est_cleared = ir_model_data.get_object(cr, uid, 'hr_workers_comp', 'est_cleared')
        est_light_duty = ir_model_data.get_object(cr, uid, 'hr_workers_comp', 'est_light_duty')
        note_history = self.pool.get('hr.workers_comp.history')
        duty_type = self.pool.get('hr.workers_comp.duty_type')
        duty_restrictions = dict([
            (r['id'], Restriction(r['id'], r['name'], r['restriction']))
            for r in duty_type.read(cr, uid, context=context)
            ])
        # get actual and estimated notes
        actual_notes = _sort_notes(notes_ids)
        estimated_notes = _sort_notes(notes_ids, estimate=True)
        if not (actual_notes or estimated_notes):
            return res
        years, restricted_300, no_duty_300, last_duty = _calc_notes(estimated_notes, estimate=True)
        actual_years, restricted, no_duty, last_duty = _calc_notes(actual_notes)
        years.update(actual_years)

        value['restriction_state_id'] = last_duty.id
        value['total_days'] = int(restricted + no_duty)
        value['total_days_300'] = int(restricted_300 + no_duty_300)
        value['restricted_duty_total'] = int(restricted)
        value['restricted_duty_total_300'] = int(restricted_300)
        value['no_duty_total'] = int(no_duty)
        value['no_duty_total_300'] = int(no_duty_300)
        year_html = (
                '<table style="width: 500px; margin-top: 0px; margin-bottom: 0px"><tbody>\n<tr style="height: 22px">'
                '<th style="padding: 0px 10px 10px; text-align: left; min-width: 100px; max-width: 100px">Year</th>'
                '<th style="padding: 0px 10px 10px; text-align: right; min-width: 150px; max-width: 150px">Days away from work</th>'
                '<th style="padding: 0px 10px 10px; text-align: right; min-width: 200px; max-width: 200px">Days restricted / Job transfer</th>'
                '<th style="padding: 0px 10px 10px; text-align: right; min-width: 50px; max-width: 50px">Total</th></tr>\n'
                )
        year_total = YearCounter('Total')
        # add yearly info
        for year in sorted(years.values(), key=lambda y: ((1, 0)[y.estimate], y.year)):
            year_html += year.html_row()
            if not year.estimate:
                year_total.full += year.full
                year_total.partial += year.partial
        # add totals
        year_html += year_total.html_row(top_margin=True)
        year_html += '</tbody></table>'
        value['days_by_year'] = year_html
        return res

    def recalc_days(self, cr, uid, *args):
        """
        recalculate lost and restricted days
        """
        _logger.info('running recalc_dates')
        # get all claims
        ids = self.search(cr, uid, [('state','=','open')])
        res = self._total_days(cr, uid, ids)
        for id, totals in res.items():
            self.write(cr, uid, id, totals)
        _logger.info('done')
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
        'active': fields.boolean('Active'),
        'name': fields.char('Description', size=128),
        'restriction': fields.selection((
                ('full', 'No duties'),
                ('light', 'Light Duties'),
                ('none', 'Normal duties'),
                ('na', 'N/A'),
            ),
            'Restriction level',
            ),
        }

    _defaults = {
        'active': True,
        }

    _sql_constraints = []


class hr_workers_comp_history(osv.Model):
    "workers comp history"
    _name = 'hr.workers_comp.history'
    _desc = "workers comp claim history entry"
    _order = "evaluation_date"

    _columns = {
        'claim_id': fields.many2one('hr.workers_comp.claim', 'Claim #'),
        'create_date': fields.date('Date note entered', readonly=True),
        'write_uid': fields.many2one('res.users', 'Entered by'),
        'evaluation_date': fields.date('Effective Date', help='date this entry takes effect', required=True, oldname='effective_date'),
        'note': fields.text('Note', required=True),
        'restriction': fields.selection((
                ('full', 'No duties'),
                ('light', 'Light Duties'),
                ('none', 'Regular duties'),
                ('est', 'Estimate'),
                ('na', 'N/A'),
            ),
            'Restriction level',
            required=True,
            ),
        'duty_id': fields.many2one('hr.workers_comp.duty_type', 'Duty Level', required=True),
        }

    def onchange_restriction(self, cr, uid, ids, restriction, duty_id, context=None):
        """
        if restriction is full, set duty_id to #restriction_full;
        otherwise, exclued #restriction_full from the allowed choices.
        """
        ir_model_data = self.pool.get('ir.model.data')
        records = ir_model_data.read(cr, uid, [('model','=','hr.workers_comp.duty_type')], fields=['name', 'res_id'], context=context)
        active = [r['res_id'] for r in records]
        full_restriction = [r['res_id'] for r in records if r['name'] in ('full_restriction', 'employee_returned_to_work')]
        light_restriction = [r['res_id'] for r in records if (r['name'].startswith('restriction') or r['name'] == 'employee_returned_to_work')]
        no_restriction = [r['res_id'] for r in records if r['name'] not in ('incomplete', 'full_restriction', 'est_light_duty', 'est_cleared')]
        estimate = [r['res_id'] for r in records if r['name'] in ('est_cleared', 'est_light_duty')]
        #
        res = {}
        domain = res['domain'] = {}
        value = res['value'] = {}
        #
        if restriction == 'full':
            domain['duty_id'] = [('id','in',full_restriction)]
            value['duty_id'] = duty_id = full_restriction[0]
            restriction_ids = full_restriction
        elif restriction == 'light':
            domain['duty_id'] = [('id','in',light_restriction)]
            restriction_ids = light_restriction
        elif restriction == 'none':
            domain['duty_id'] = [('id','in',no_restriction)]
            restriction_ids = no_restriction
        elif restriction == 'est':
            domain['duty_id'] = [('id','in',estimate)]
            restriction_ids = estimate
        elif restriction == 'na':
            domain['duty_id'] = [('id','=',0)]
            value['duty_id'] = duty_id = False
            restriction_ids = []
        else: # restriction is False
            if duty_id and duty_id not in active:
                # but duty is not, and is an old code
                restriction_ids = [duty_id]
            else:
                value['duty_id'] = duty_id = False
                restriction_ids = []
        #
        if duty_id not in restriction_ids:
            value['duty_id'] = False
        return res


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

    fields.apply_groups(
        _columns,
        {'base.group_hr_manager': ['worker_comp_claim_ids']},
        )


class DayCounter(object):

    def __init__(self, value=0):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, (self.__class__, int, long)):
            return NotImplemented
        if isinstance(other, self.__class__):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        if not isinstance(other, (self.__class__, int, long)):
            return NotImplemented
        if isinstance(other, self.__class__):
            return self.value != other.value
        else:
            return self.value != other

    def __ge__(self, other):
        if not isinstance(other, (self.__class__, int, long)):
            return NotImplemented
        if isinstance(other, self.__class__):
            return self.value >= other.value
        else:
            return self.value >= other

    def __gt__(self, other):
        if not isinstance(other, (self.__class__, int, long)):
            return NotImplemented
        if isinstance(other, self.__class__):
            return self.value > other.value
        else:
            return self.value > other

    def __lt__(self, other):
        if not isinstance(other, (self.__class__, int, long)):
            return NotImplemented
        if isinstance(other, self.__class__):
            return self.value < other.value
        else:
            return self.value < other

    def __le__(self, other):
        if not isinstance(other, (self.__class__, int, long)):
            return NotImplemented
        if isinstance(other, self.__class__):
            return self.value <= other.value
        else:
            return self.value <= other

    def __add__(self, other):
        if isinstance(other, self.__class__):
            value = self.value + other.value
        elif isinstance(other, int):
            value = self.value + other
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            value = self.value + other.days
        else:
            return NotImplemented
        return self.__class__(value)

    __radd__ = __add__

    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            self.value += other.value
        elif isinstance(other, int):
            self.value += other
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            self.value += other.days
        else:
            return NotImplemented
        return self

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            value = self.value - other.value
        elif isinstance(other, int):
            value = self.value - other
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            value = self.value - other.days
        else:
            return NotImplemented
        return self.__class__(value)

    def __rsub__(self, other):
        if isinstance(other, self.__class__):
            value = other.value - self.value
        elif isinstance(other, int):
            value = other - self.value
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            value = other.days - self.value
        else:
            return NotImplemented
        return self.__class__(value)

    def __isub__(self, other):
        if isinstance(other, self.__class__):
            self.value -= other.value
        elif isinstance(other, int):
            self.value -= other
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            self.value -= other.days
        else:
            return NotImplemented
        return self

    def __mul__(self, other):
        if isinstance(other, self.__class__):
            value = self.value * other.value
        elif isinstance(other, int):
            value = self.value * other
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            value = self.value * other.days
        else:
            return NotImplemented
        return self.__class__(value)

    __rmul__ = __mul__

    def __imul__(self, other):
        if isinstance(other, self.__class__):
            self.value *= other.value
        elif isinstance(other, int):
            self.value *= other
        elif isinstance(other, timedelta):
            if other.seconds:
                return NotImplemented
            self.value *= other.days
        else:
            return NotImplemented
        return self

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'DayCounter(%r)' % self.value

    def __str__(self):
        return str(self.value)


class YearCounter(object):

    def __init__(self, year, full=None, partial=None, estimate=False):
        if full is None:
            full = DayCounter()
        if partial is None:
            partial = DayCounter()
        self.year = year
        self.full = full
        self.partial = partial
        self.estimate = estimate

    def __repr__(self):
        return (
                'YearCounter(%s, full=%s, partial=%s, estimate=%s)'
                % (self.year, self.full, self.partial, self.estimate)
                )

    def __nonzero__(self):
        return (self.estimate is False) or (self.full+self.partial > 0)
    __bool__ = __nonzero__

    def html_row(self, top_margin=False):
        if self and self.estimate:
            return (
                '<tr style="height: 22px" bgcolor="eeeeee">'
                '<th style="padding: 8px 10px 2px">%s estimate</th>'
                '<td style="padding: 8px 10px 2px; text-align: right">%s</td>'
                '<td style="padding: 8px 10px 2px; text-align: right">%s</td>'
                '<td style="padding: 8px 10px 2px; text-align: right; border-left: 1px solid #dddddd">%s</td>'
                '</tr>\n'
                % (self.year, self.full, self.partial, self.full+self.partial)
                )
        elif self and top_margin:
            return (
                '<tr style="height: 22px">'
                '<th style="padding: 8px 10px 2px">%s</th>'
                '<td style="padding: 8px 10px 2px; text-align: right; border-top: 1px solid #dddddd">%s</td>'
                '<td style="padding: 8px 10px 2px; text-align: right; border-top: 1px solid #dddddd">%s</td>'
                '<td style="padding: 8px 10px 2px; text-align: right; border-top: 1px solid #dddddd; border-left: 1px solid #dddddd">%s</td>'
                '</tr>\n'
                % (self.year, self.full, self.partial, self.full+self.partial)
                )
        elif self:
            return (
                '<tr style="height: 22px">'
                '<th style="padding: 8px 10px 2px">%s</th>'
                '<td style="padding: 8px 10px 2px; text-align: right">%s</td>'
                '<td style="padding: 8px 10px 2px; text-align: right">%s</td>'
                '<td style="padding: 8px 10px 2px; text-align: right; border-left: 1px solid #dddddd">%s</td>'
                '</tr>\n'
                % (self.year, self.full, self.partial, self.full+self.partial)
                )
        else:
            return ('<tr style="height: 22px" bgcolor="ffe6ea">'
            '<th style="padding: 8px 10px 2px">%s estimate</th>'
            '<td style="padding: 8px 10px 2px; text-align: center" colspan="2">M I S S I N G</td>'
            '<td style="border-left: 1px solid #dddddd"></td>'
            '</tr>'
            % self.year
            )


class Note(NamedTuple):
    restriction = 0
    date = 1
    duty_id = 2


class Restriction(NamedTuple):
    id = 0
    name = 1
    restriction = 2


class OldStyleRestriction(Exception):
    pass

class InvalidNote(Exception):
    pass
