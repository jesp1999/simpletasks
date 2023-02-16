import argparse
from enum import Enum
from pathlib import Path
from sqlite3 import Row
from typing import Sequence
import datetime as dt

import sqlite3

import sys
from os import getenv


class State(Enum):
    MENU = 'm'
    ADD = 'a'
    LIST = 'l'
    UPDATE = 'u'
    EXIT = 'x'


def get_user_data_dir(appname: str) -> Path:
    if sys.platform == "win32":
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        dir_, _ = winreg.QueryValueEx(key, "Local AppData")
        ans = Path(dir_).resolve(strict=False)
    elif sys.platform == 'darwin':
        ans = Path('~/Library/Application Support/').expanduser()
    else:
        ans = Path(getenv('XDG_DATA_HOME', "~/.local/share")).expanduser()
    return ans.joinpath(appname)


APP_NAME = 'simpletasks'
user_data_dir = get_user_data_dir(appname=APP_NAME)
if not user_data_dir.is_dir():
    user_data_dir.mkdir()

db_file = Path(
    user_data_dir,
    'tasks.db'
)
print(db_file)
conn = sqlite3.connect(db_file)
conn.row_factory = Row
cursor = conn.cursor()


def initialize_data_store():
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS tasks'
        '(completed BOOLEAN, priority TINYINT, task_name TEXT, '
        'status TEXT, label TEXT, due_date TEXT);',
    )
    conn.commit()


def task_pretty(priority, task_name, status, label, due_date):
    return f'[{priority}] {task_name}({label}) - {status}, due {due_date}'


def menu() -> State:
    print(
        f'welcome to {APP_NAME}!\n'
        '(a)dd task\n'
        '(l)ist tasks\n'
        '(u)pdate task\n'
        'e(x)it'
    )
    user_input = input('> ')
    print('\n')
    if user_input.casefold() == 'a':
        state = State.ADD
    elif user_input.casefold() == 'l':
        state = State.LIST
    elif user_input.casefold() == 'u':
        state = State.UPDATE
    elif user_input.casefold() == 'x':
        state = State.EXIT
    else:
        print('invalid input!\n')
        state = State.MENU
    return state


def add_task() -> State:
    task_name = input('name? ')
    task_priority = int(input('priority? 0(hi)-255(low) [10]\t') or 10)
    task_label = input('label? [misc]\t') or 'misc'
    task_status = input('status? [not started]\t') or 'not started'
    today_str = dt.datetime.now().strftime("%m-%d-%y")
    task_due = dt.datetime.strptime(
        input(f'due? [{today_str}]\t') or today_str, '%m-%d-%y'
    )
    cursor.execute(
        'INSERT INTO tasks '
        '(completed, priority, task_name, status, label, due_date) '
        'VALUES (false, ?, ?, ?, ?, ?);',
        (task_priority, task_name, task_status, task_label, task_due)
    )
    conn.commit()
    print('task added!\n')
    return State.MENU


def list_tasks() -> State:
    rows: list[Row] = cursor.execute(
        'SELECT priority, task_name, status, label, due_date '
        'FROM tasks WHERE completed=false ORDER BY priority, due_date;'
    ).fetchall()
    tasks_pretty = '\n'.join([task_pretty(
        r['priority'], r['task_name'], r['status'], r['label'], r['due_date']
    ) for r in rows])
    print('current tasks:')
    print(tasks_pretty)
    print('\n')
    return State.MENU


# TODO enable more updating options than just completing
def update_task() -> State:
    rows: list[Row] = cursor.execute(
        'SELECT task_name FROM tasks WHERE completed=false '
        'ORDER BY priority, due_date;'
    ).fetchall()
    task_names = [r['task_name'] for r in rows]
    print('pending tasks:')
    print(', '.join(task_names), '\n')
    print('which task to update?')
    user_input = input('> ')
    if user_input in task_names:
        cursor.execute(
            'UPDATE tasks SET completed=true WHERE task_name=?;', user_input
        )
    else:
        print('task not found!\n')
    return State.MENU


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Task list CLI')
    parser.parse_args(argv)
    initialize_data_store()
    state = State.MENU
    while state != State.EXIT:
        if state == State.MENU:
            state = menu()
        elif state == State.ADD:
            state = add_task()
        elif state == State.LIST:
            state = list_tasks()
        elif state == State.UPDATE:
            state = update_task()
        else:
            raise RuntimeError('invalid state!\n')
    print('bye!')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
