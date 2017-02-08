import logging
from osv import osv, fields
from dbf import Date

_logger = logging.getLogger(__name__)

class hr_workers_comp_claim(osv.Model):
    "workers comp information fields"
    _name = 'hr.workers_comp.claim'

    def _total_days(self, cr, uid, ids, field_names=None, arg=None, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        records = self.read(
                cr, uid, ids,
                fields=[
                    'id', 'injury_date', 'full_duty_return',
                    'restricted_duty_start', 'restricted_duty_end',
                    'no_duty_start', 'no_duty_end',
                    ],
                context=context,
                )
        for rec in records:
            id = rec['id']
            inj, fdr = rec['injury_date'], rec['full_duty_return']
            rds, rde = rec['restricted_duty_start'], rec['restricted_duty_end']
            nds, nde = rec['no_duty_start'], rec['no_duty_end']
            res[id] = self.onchange_dates(
                    cr, uid, id,
                    inj, fdr, nds, nde, rds, rde,
                    context=context,
                    )['value']
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
        'injury_id': fields.many2one('hr.workers_comp.injury', 'Injury'),
        'injury_date': fields.date('Injury Date'),
        'location_id': fields.many2one('hr.department', 'Location of Accident'),
        'notes': fields.text('Notes'),
        'state_claim_id': fields.char('State Claim Number', size=64),
        'resolution_id': fields.many2one('hr.workers_comp.resolution', 'Resolution'),
        'full_duty_return': fields.date('Return to full duty'),
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
            ),
        'restricted_duty_start': fields.date('Start date of restricted duty'),
        'restricted_duty_end': fields.date('End date of restricted duty'),
        'restricted_duty_total': fields.function(
            _total_days,
            type='integer',
            string='Total restricted days',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['injury_date', 'restricted_duty_start', 'restricted_duty_end'],
                    10,
                    ),
                },
            ),
        'no_duty_start': fields.date('Start date of full restriction'),
        'no_duty_end': fields.date('End date of full restriction'),
        'no_duty_total': fields.function(
            _total_days,
            type='integer',
            string='Total full restriction days',
            multi='dates',
            store={
                'hr.workers_comp.claim': (
                    lambda table, cr, uid, ids, ctx=None: ids,
                    ['injury_date', 'no_duty_start', 'no_duty_end'],
                    10,
                    ),
                },
            ),
        }

    def onchange_dates(self, cr, uid, ids, inj, fdr, nds, nde, rds, rde, context=None):
        res = {}
        res['value'] = value = {}
        today = Date(fields.date.context_today(self, cr, uid, context=context))
        inj, fdr = Date(inj or None), Date(fdr or None) or today
        rds, rde = Date(rds or None), Date(rde or None) or today
        nds, nde = Date(nds or None), Date(nde or None) or today
        if inj:
            value['full_duty_lost'] = (fdr - inj).days
        if rds:
            value['restricted_duty_total'] = (rde - rds).days
        if nds:
            value['no_duty_total'] = (nde - nds).days
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


class hr_workers_comp_injury(osv.Model):
    "workers comp injury"
    _name = 'hr.workers_comp.injury'

    _columns = {
        'name': fields.char('Description', size=128),
        }

    _sql_constraints = [
            ('injury_uniq', 'unique(name)', 'This injury already exists.'),
            ]

class hr_workers_comp_resolution(osv.Model):
    "workers comp claim resolution"
    _name = 'hr.workers_comp.resolution'

    _columns = {
        'name': fields.char('Description', size=128),
        }

    _sql_constraints = [
            ('resolution_uniq', 'unique(name)', 'This resolution already exists.'),
            ]

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
