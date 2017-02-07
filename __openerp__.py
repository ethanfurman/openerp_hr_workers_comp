# -*- coding: utf-8 -*-

{
    'name' : 'Workers Compensation Management',
    'version' : '0.1',
    'author' : 'Ethan Furman',
    'sequence': 116,
    'category': 'Human Resources',
    'summary' : 'Manage workers compensation claims for employees',
    'description' : """
Manage Workers Compensation claims
==================================

This application allows you to track injuries by department, type, and time lost.
""",
    'depends' : [
        'base',
        'hr',
        ],
    'data' : [
        'hr_workers_comp_view.xaml',
        'security/ir.model.access.csv',
        ],

    'installable' : True,
    'auto_install': False,
    'application': True,
}
