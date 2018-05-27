#!/home/andrey/anaconda3/bin/python3

import argparse
import os
import pickle
import shutil
import subprocess
from copy import deepcopy


def rm_r(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def find_dupes(dir, minsize):
    print('Searching dupes from {}'.format(dir))
    output = subprocess.run(["fdupes", "-S", "-n", "-r", dir], stdout=subprocess.PIPE).stdout.decode()
    with open('raw-dups-report.log', 'w') as f:
        f.write(output)
    files = output.split('\n\n')
    result = []
    for f in files:
        if len(f):
            size_bytes = int(f.split('\n')[0].split(' ')[0])
            paths = f.split('\n')[1:]
            result.append({'size': size_bytes, 'files': paths})
    res = sorted([f for f in result if f['size'] >= minsize * 1024 * 1024], key=lambda x: x['size'], reverse=True)
    files_to_delete = deepcopy(res)
    total_saved_space = 0
    for f in files_to_delete:
        f['files'] = sorted(f['files'])
        total_saved_space += f['size'] * (len(f['files']) - 1)
    total_saved_space = total_saved_space
    summary = {'total_saved_space': total_saved_space, 'files_to_delete': files_to_delete, 'scanned_dir': dir}
    write_summary_to_files(summary)


def write_summary_to_files(summary):
    with open('dups-report.log', 'w') as f:
        f.write('Scan root: %s\n' % summary['scanned_dir'])
        f.write('Saved space (Mb): {}\n\n'.format(summary['total_saved_space'] / 1024 ** 2))  # Mbytes
        f.write('\n'.join(
            ['\/' * 5 + str(f['size']) + '\/' * 5 + '\n' + '\n'.join(f['files']) + '\n' + '/\\' * 10
             for f in summary['files_to_delete']]))
    with open('files_to_delete.pkl', 'wb') as f:
        pickle.dump(summary, f)


def skip_or_remove(root, mode=None):
    with open('files_to_delete.pkl', 'rb') as f:
        summary = pickle.load(f)
    original_total_saved_space = summary['total_saved_space']
    for files in summary['files_to_delete']:
        if root == None:
            remaining_files = []
            matching_files = []
            files_by_dirname = {}
            for fn in files['files']:
                if os.path.dirname(fn) not in files_by_dirname:
                    files_by_dirname[os.path.dirname(fn)] = []
                files_by_dirname[os.path.dirname(fn)].append(fn)
            for v in files_by_dirname.values():
                remaining_file = min(v, key=lambda x: os.path.getmtime(x))
                remaining_files.append(remaining_file)
                matching_files += list(filter(lambda x: x != remaining_file, v))
        else:
            matching_files = [f for f in files['files'] if f.startswith(root)]
            remaining_files = [f for f in files['files'] if not f.startswith(root)]
        # VERY IMPORTANT!!! LEAVE SOME FILES!!!
        if not remaining_files:
            continue
        if mode and matching_files:
            for mf in matching_files:
                print(('(SIMULATION) ' if mode == 'sim' else '') + 'Deleting: ' + mf)
                if mode == 'rm':
                    rm_r(mf)
        not_saved_space = (len(files['files']) - len(remaining_files)) * files['size']
        files['files'] = remaining_files
        summary['total_saved_space'] -= not_saved_space
    summary['files_to_delete'] = [f for f in summary['files_to_delete'] if len(f['files']) > 1]
    if mode == 'sim':
        print('\n\nDeleted Bytes:' + str(original_total_saved_space - summary['total_saved_space']))
    else:
        write_summary_to_files(summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('mode', nargs=1, default='scan', help='scan, skip, rm, sim')
    parser.add_argument('-p', help='Duplicate search root path', default=None)
    parser.add_argument('-s', help='Min size of a file, MB', default=0)

    args = parser.parse_args()

    abs_path = os.path.abspath(args.p) if args.p != None else None
    if args.mode[0] == 'scan':
        find_dupes(abs_path, float(args.s))
    if args.mode[0] == 'skip':
        skip_or_remove(abs_path)
    if args.mode[0] == 'rm' or args.mode[0] == 'sim':
        if args.mode[0] == 'rm':
            skip_or_remove(abs_path, 'sim')
            confirmation = input("!!!!! RUNNING IN RM MODE, type YES to continue !!!!!\n")
            if confirmation != 'YES':
                raise Exception('Unconfirmed RM')
        skip_or_remove(abs_path, args.mode[0])
