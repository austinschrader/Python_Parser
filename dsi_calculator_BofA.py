# -*- coding: utf-8 -*-
"""
Created on Wed Mar 20 16:21:01 2019

@author: Megan.Francis
"""

import pandas as pd
import pyodbc as pyo
import math
from sqlalchemy import create_engine

pool = input('Which pool?')
stage = input('FINAL or PRELIM?')
#directory = input('Where is the pay history?')


def get_history():
    directory = 'U:\\Megan.Francis\\My Documents\\Python Scripts\\555 Loan Train LNTRN Final.xlsx'
    history = pd.read_excel(directory)
    
    return history
hist = get_history()

def get_loan_hist(loan):
    loan_hist = hist[hist['ACCT#'] == int(loan)]
              
    return loan_hist                      
              
def get_date_rec(loan):
    loan_hist = get_loan_hist(loan)
    date_rec = loan_hist[loan_hist['TRNINT'] > 0]['TRNDTE'].max()
    
    return date_rec
            

def get_conn():
    conn = pyo.connect('DSN=BoardingServerTest;Trusted_Connection=yes;')
        
    return conn

#Querys the pool database to get the population of DSIs to check
def get_pop(pool,stage):
    conn = get_conn()
    query = 'SELECT [Account], [OldLoanNumber], [NoteRate], CAST([daterec] as datetime) as daterec, [Prinbal] FROM ' + 'Pool' + pool  + '.dbo.Boardingtape_' + stage + ' WHERE [DSIFlag] = \'1\' and LoanStatus <> \'Inactive - Interim PIF\''
    pop = pd.read_sql(query,conn)    
    conn.close()
    pop = pop.set_index('OldLoanNumber')
    
    return pop
pop = get_pop(pool, stage)


#Gets the last principal paid date. 
#Current Assumptions:
    #Any principal application means all interest was paid  
    #The rate has not changed since prin_date
    #Interest is calculated on a 365 day basis
def get_int_due(loan):
    loan_hist = get_loan_hist(loan)
    loan_data = pop.loc[str(loan)]
    prin_date = loan_hist[loan_hist['TRNPRN'] > 0]['TRNDTE'].max()
    date_rec = get_date_rec(loan)
    days_int = (date_rec - prin_date).days
    int_charged = math.floor(days_int * loan_data['Prinbal'] * loan_data['NoteRate']/365)/100
    int_paid = loan_hist[loan_hist['TRNDTE'] > prin_date]['TRNINT'].sum()
    
    return (int_charged - int_paid)


def get_pop_int_due():
    pop_int_due = pd.DataFrame(columns = ['Account','UnpaidInterest','DateRec'])
    
    i = 0
    for loan in pop.index:
        Account  = pop.loc[str(loan), 'Account']
        int_due = get_int_due(loan)
        date_rec = get_date_rec(loan)
        pop_int_due.loc[i, 'Account'] = Account
        pop_int_due.loc[i, 'UnpaidInterest'] = int_due
        pop_int_due.loc[i, 'DateRec'] = date_rec
        i = i + 1
        
    return pop_int_due


def import_int_due():
    data = get_pop_int_due()
    use_pool = 'Use Pool' + pool
    engine = create_engine('mssql+pyodbc://BoardingServerTest')
    engine.execute(use_pool)
    conn = engine.connect()
    table_name = 'P' + pool + '_' + stage + '_UnpaidInterest_Python'
    data.to_sql(name = table_name, con = conn, if_exists = 'replace', index = False)
    conn.close()
    
    return True
    