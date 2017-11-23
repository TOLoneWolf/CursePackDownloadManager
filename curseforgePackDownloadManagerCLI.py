import os
from downloader_core import *
import sys

'''
Author(s): TOLoneWolf

This contains the code used to make the command line interface.
'''

def isInt(source):
    try:
        intresult = int(source)
    except: return False
    return True


if __name__ == '__main__':

    program_title = PROGRAM_NAME + ' v' + PROGRAM_VERSION_NUMBER + " " + PROGRAM_VERSION_BUILD
    print('\n' + '-' * len(program_title))
    print(program_title)
    print('-' * len(program_title))

    initialize_program_environment()

    program_options_list = ['install from curse', 'check instance(s) update']
    print('What would you like to do today?')

    user_selection = False
    while not user_selection:
        for x in range(1, len(program_options_list) + 1):
            print(str(x) + ') ' + str(program_options_list[x-1]))
        users_response = input(':')
        users_response = users_response.strip()
        if isInt(users_response):
            if (int(users_response) >= 1) and (int(users_response) <= len(program_options_list)):
                print('correct')
                user_selection = True
                pass

