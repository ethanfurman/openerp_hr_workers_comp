import unittest2
# from openerp.osv.orm import BaseModel
import openerp.tests.common as common


class TestCalculations(common.TransactionCase):

    def setUp(self):
        super(TestCalculations, self).setUp()
        self.hr_claim = self.registry('hr.workers_comp.claim')
        self.hr_history = self.registry('hr.workers_comp.history')
        self.heavy_restriction_id = self.ref('hr_workers_comp.duty_full')
        self.light_restriction_id = self.ref('hr_workers_comp.duty_five')
        self.no_restriction_id = self.ref('hr_workers_comp.duty_cleared')
        self.quit_restriction_id = self.ref('hr_workers_comp.duty_quit')

    def test_onchange_dates(self):
        cr, uid = self.cr, self.uid
        ocd = self.hr_claim.onchange_dates(
                cr, uid, [],
                '2017-02-07',
                [
                    [5, False, False],
                    [0, 0, {'effective_date': '2017-02-07', 'duty_id': self.light_restriction_id}],
                    [0, 0, {'effective_date': '2017-02-14', 'duty_id': self.heavy_restriction_id}],
                    [0, 0, {'effective_date': '2017-02-21', 'duty_id': self.light_restriction_id}],
                    [0, 0, {'effective_date': '2017-02-28', 'duty_id': self.no_restriction_id}],
                    ],
                )
        value = ocd['value']
        self.assertEqual(value['full_duty_lost'], 14)
        self.assertEqual(value['restricted_duty_total'], 10)
        self.assertEqual(value['no_duty_total'], 4)
        note_ids = []
        note_ids.append(self.hr_history.create(
            cr, uid,
            {'effective_date': '2017-02-07', 'duty_id': self.light_restriction_id}
            ))
        note_ids.append(self.hr_history.create(
            cr, uid,
            {'effective_date': '2017-02-14', 'duty_id': self.heavy_restriction_id}
            ))
        note_ids.append(self.hr_history.create(
            cr, uid,
            {'effective_date': '2017-02-21', 'duty_id': self.light_restriction_id}
            ))
        note_ids.append(self.hr_history.create(
            cr, uid,
            {'effective_date': '2017-02-28', 'duty_id': self.no_restriction_id}
            ))
        notes = self.hr_history.browse(cr, uid, note_ids)
        ocd = self.hr_claim.onchange_dates(cr, uid, [], '2017-02-07', notes)
        value = ocd['value']
        self.assertEqual(value['full_duty_lost'], 14)
        self.assertEqual(value['restricted_duty_total'], 10)
        self.assertEqual(value['no_duty_total'], 4)

    def test_create_and_write(self):
        cr, uid = self.cr, self.uid
        # print('creating claim')
        new_claim_id = self.hr_claim.create(
                cr, uid,
                {
                    'state':'open',
                    'restriction_state': 'light',
                    'injury_date': '2017-02-07',
                    },
                )
        # print('new claim id:', new_claim_id)
        note_id_1 = self.hr_history.create(
                cr, uid,
                {
                    'claim_id': new_claim_id,
                    'effective_date': '2017-02-07',
                    'duty_id': self.light_restriction_id,
                    },
                )
        # print('new note id:', note_id_1)
        note_id_2 = self.hr_history.create(
                cr, uid,
                {
                    'claim_id': new_claim_id,
                    'effective_date': '2017-02-14',
                    'duty_id': self.no_restriction_id,
                    },
                )
        # print('new note id:', note_id_2)
        self.assertTrue(
                self.hr_claim.write(cr, uid, new_claim_id, {'notes_ids': [(6, 0, [note_id_1, note_id_2])]})
                )
        # test
        # claim = hr_claim.browse(cr, uid, new_claim_id)
        # print(claim.injury_date)
        # print(claim.full_duty_lost)
        # print(claim.restricted_duty_total)
        # print(claim.no_duty_total)
        # self.assertTrue(claim.full_duty_lost == claim.no_duty_total == claim.restricted_duty_total == 0)
        # self.assertEqual(claim.restricted_duty_total, 5)
        [claim] = self.hr_claim.read(
                cr, uid, [new_claim_id],
                fields=['full_duty_lost', 'no_duty_total', 'restricted_duty_total'],
                )
        self.assertEqual(claim['no_duty_total'], 0)
        self.assertEqual(claim['full_duty_lost'], 5)
        self.assertEqual(claim['restricted_duty_total'], 5)
        #
        self.hr_history.write(cr, uid, note_id_2, {'effective_date': '2017-02-21'})
        [claim] = self.hr_claim.read(
                cr, uid, [new_claim_id],
                fields=['full_duty_lost', 'no_duty_total', 'restricted_duty_total'],
                )
        self.assertEqual(claim['no_duty_total'], 0)
        self.assertEqual(claim['full_duty_lost'], 9)
        self.assertEqual(claim['restricted_duty_total'], 9)

if __name__ == '__main__':
    unittest2.main()
