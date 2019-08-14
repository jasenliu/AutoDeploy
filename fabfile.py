from fabric import Connection
from invoke import task
import time
import logging
import tqdm

#logging.basicConfig(format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',level=logging.INFO,filename='{0}_release.log'.format(time.strftime("%y%m%d")))

filename = '{0}_release.log'.format(time.strftime("%y%m%d"))
file_handler = logging.FileHandler(filename)
console_handler = logging.StreamHandler()
file_handler.setLevel('INFO')
console_handler.setLevel('INFO')
fmt = '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
formatter = logging.Formatter(fmt)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')
logger.addHandler(file_handler)
logger.addHandler(console_handler)

#env.shell="cmd /c"

'''
1. prepare release package and named it like yymmdd.zip(eg 190806.zip)
2. put release package to your local_update_files_folder which you can change it by yourself
3. open cmd window execute related command(eg fab deploy-production dll 190806)
'''

def show_progress_bar(*args, **kwargs):
    pbar = tqdm.tqdm(*args, **kwargs)  # make a progressbar
    last = [0]  # last known iteration, start at 0
    def viewBar(transferred, to_be_transferred):
        pbar.total = int(to_be_transferred)
        pbar.update(int(transferred- last[0]))  # update pbar with increment
        last[0] = transferred  # update last known iteration
    return viewBar, pbar  # return callback, tqdmInstance


def progress_bar(transferred, toBeTransferred, suffix=''):
    # print "Transferred: {0}\tOut of: {1}".format(transferred, toBeTransferred)
    bar_len = 60
    filled_len = int(round(bar_len * transferred/float(toBeTransferred)))
    percents = round(100.0 * transferred/float(toBeTransferred), 1)
    bar = '#' * filled_len + '-' * (bar_len - filled_len)
    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()

'''
file_type='web',only update web files, cmd command is 'fab deploy-production web package_name'
file_type='dll', udpate both web files and dlls, cmd command is 'fab deploy-production dll package_name'
'''
@task
def deploy_production(c, file_type, package_name):
    #current_day = time.strftime("%y%m%d")
    # print(current_day)
    local_update_files_folder = 'e:/release_files/'
    remote_update_files_folder = '/cygdrive/c/update_files/'
    remote_backup_folder = '/cygdrive/c/update_files/production_web_backup/'
    remote_web_site_folder = '/cygdrive/c/progra~2/THC/'
    conn = Connection(host='11.11.11.10', user='Administrator',
                      connect_kwargs={'password': "THCNetwork1@3"})
    with conn.cd(remote_update_files_folder):
        logger.info('begin to upload file...')
        begin_time = time.time()
        cbk, pbar = show_progress_bar(ascii=True, unit='b', unit_scale=True)
        result = conn.sftp().put("{0}{1}.zip".format( local_update_files_folder, package_name), "%s%s.zip"%(remote_update_files_folder,package_name), callback=cbk)
        pbar.close()
        # conn.sftp().put("{0}{1}.zip".format( local_update_files_folder, package_name), remote_update_files_folder + package_name + ".zip", callback=progress_bar)
        end_time = time.time()
        logger.info('file upload finished...')
        logger.info("Uploaded {0}{1}.zip -> {2}{1}.zip".format(local_update_files_folder, package_name, remote_update_files_folder))
        logger.info("used {:.5}s".format(end_time - begin_time))
        time.sleep(1)
        logger.info('unzip the uploaded files...')
        conn.run("unzip -o {0}.zip -d .".format(package_name))
    with conn.cd(remote_backup_folder):
        conn.run('rm -rf ./thc/*')
        logger.info('copy files to the backup folder...')
        conn.run("cp -a -f -v ../{0}/* ./thc/".format(package_name))
        logger.info('backup the files ...')
        conn.run("./backup_thc.bat")
        if file_type == 'dll':
            logger.info('stopping service...')
            conn.run('{0}stop.bat'.format(remote_web_site_folder))
            logger.info('update release files ...')
            #conn.run('cp -a -f -v ./thc/* {0}'.format(remote_web_site_folder))
            conn.run("./copy_to_thc.bat")
            logger.info('starting service ...')
            conn.run('{0}start.bat'.format(remote_web_site_folder))
        else:
            logger.info('update release files ...')
            #conn.run('cp -a -f -v ./thc/* {0}'.format(remote_web_site_folder))
            conn.run("./copy_to_thc.bat")
        logger.info('deploy finished.')


@task
def update_pcnest(c):
    remote_pcnest_dir = '/cygdrive/d/THC/IRRSvc'
    for host in ['11.11.11.18', '11.11.11.28', '11.11.11.38']:
        conn = Connection(host, user='Administrator',
                          connect_kwargs={'password': "THCcalc123"})
        logger.info(host)
        conn.run('uname -s')
        with conn.cd(remote_pcnest_dir):
            conn.run('./kill.bat')
            conn.run('../update_irrsvc.bat')
        logger.info('{0} pcnest update completed.'.format(host))
    logger.info('all the pcnest update completed.')


@task
def restart_pcnest(c):
    remote_pcnest_dir = '/cygdrive/d/THC/IRRSvc'
    for host in ['11.11.11.18', '11.11.11.28', '11.11.11.38']:
        conn = Connection(host, user='Administrator',
                          connect_kwargs={'password': "THCcalc123"})
        with conn.cd(remote_pcnest_dir):
            conn.run('./kill.bat')
            conn.run('./IRRSvc_u.bat')
            conn.run('./IRRSvc_i.bat')
        logger.info('{0} pcnest restart completed.'.format(host))
    logger.info('all the pcnest restart completed.')
