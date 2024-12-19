import os
import time
import numpy as np
import requests
from dlnpyutils import utils as dln
import re
from glob import glob
import json
import subprocess
import shutil

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def getids(year=None,month=None,clobber=False):
    """ Get arxiv IDs for each month for the last 10 years."""

    if year is None:
        year = np.arange(10)+2015
    if month is None:
        month = np.arange(12)+1
    
    for y in year:
        for m in month:
            outfile = 'ids/arxiv_ids_{:04d}-{:02d}.txt'.format(y,m)
            if os.path.exists(outfile)==False or clobber:
                url = 'https://arxiv.org/list/astro-ph/{:04d}-{:02d}?skip=0&show=2000'.format(y,m)
                r = requests.get(url)
                text = r.content.decode()
                lines = text.split('\n')
                lines = [d for d in lines if d.find('Abstract')>-1 and d.find('id=')>-1]
                lines = [d.split('id=')[-1] for d in lines]
                ids = [d.replace('"','').replace('>','') for d in lines]
                print(y,m,len(ids))
                dln.writelines(outfile,ids)
                
def gettext(name,method='html'):
    """ Get text for each paper."""
    # Input the arXiv ID, i.e. 2401.00185

    t0 = time.time()
    
    # HTML
    if method=='html':
        #r = requests.get('https://arxiv.org/html/2412.12249v1')
        r = requests.get('https://arxiv.org/html/'+name+'v1')
        if r.ok:
            text = r.content.decode()
            # need to remove all of the html tags
            out = remove_html_tags(text)
        else:
            print('html request not okay')
            out = None
    
    # TEX source
    elif method=='source':
        url = 'https://arxiv.org/src/'+name
        r1 = requests.get(url)
        if r1.ok==False:
            print('problem downloading source')
            time.sleep(0.2)
            return None
        tempfile = name+'.tar.gz'
        if os.path.exists(tempfile): os.remove(tempfile)
        with open(tempfile,'wb') as f:
            f.write(r1.content)
        os.makedirs('temp',exist_ok=True)
        shutil.move(tempfile,'temp/'+tempfile)
        curdir = os.getcwd()
        os.chdir('temp')
        r2 = subprocess.run(['tar','-xvf',tempfile],shell=False,capture_output=True)
        if r2.returncode != 0:
            print('problem unpacking source')
            os.chdir(curdir)
            shutil.rmtree('temp')
            time.sleep(0.2)
            return None
        texfiles = glob('*.tex')
        if len(texfiles)==0:
            print('no tex files found')
            os.chdir(curdir)
            shutil.rmtree('temp')
            time.sleep(0.2)
            return None
        # multiple tex files
        if len(texfiles)>1:
            # look for "documentclass" in the file
            r3 = subprocess.run(['grep','documentclass']+texfiles,shell=False,capture_output=True)
            if r3.returncode != 0:
                # will also return 1 if no matches found
                print('multiple tex files. unclear which one to use')
                os.chdir(curdir)
                shutil.rmtree('temp')
                time.sleep(0.2)
                return None
            greplines = r3.stdout.decode().split('\n')
            texfiles = greplines[0].split(':')[0]
        else:
            texfiles = texfiles[0]
        # Load the tex file
        try:
            out = dln.readlines(texfiles)
            out = '\n'.join(out)
        except:
            print('problem reading tex file')
            out = None
        # Removing temporary files
        os.chdir(curdir)
        shutil.rmtree('temp')
    
    # PDF
    elif method=='pdf':
        url = 'https://arxiv.org/pdf/'+name
        r1 = subprocess.run(['wget',url],shell=False,capture_output=True)
        if r1.returncode != 0:
            print('problem getting pdf')
            time.sleep(0.2)
            return None
        r2 = subprocess.run(['gs','-sDEVICE=txtwrite','-o',name+'_gs.txt',name],
                            shell=False,capture_output=True)
        if r2.returncode != 0:
            print('problem scraping text from pdf')
            time.sleep(0.2)
            return None
        #with open(name+'_gs.txt','rb') as f:
        #    out = f.readlines()
        #out = [o.decode() for o in out]
        try:
            out = dln.readlines(name+'_gs.txt')
            out = '\n'.join(out)
        except:
            print('problem reading scraped pdf text')
            out = None
        # Delete temporary files
        if os.path.exists(name): os.remove(name)
        if os.path.exists(name+'_gs.txt'): os.remove(name+'_gs.txt')
    else:
        raise Exception(str(method)+' not supported')

    # Wait to make sure we don't overload the system
    dt = time.time()-t0
    if dt < 0.2:
        time.sleep(0.2)
                    
    return out

def searchtext(text):
    """ Search article text for Python/Julia terms."""
    ltext = text.lower()
    out = {}
    for c in ['python','numpy','scipy','astropy','sklearn','julia']:
        out[c] = ltext.find(c)>-1
    return out

def bigsearch(year=None,clobber=False):
    """ Loop over all arxiv ids, get the text and search for python/julia """

    if year is not None:
        idfiles = glob('ids/arxiv_ids_{:04d}*.txt'.format(int(year)))
    else:
        idfiles = glob('ids/arxiv_ids*.txt')
    idfiles.sort()
    ids = []
    for f in idfiles:
        lines = dln.readlines(f)
        ids += lines
    ids = np.unique(ids)
    print(len(ids),'ids')
    
    # Loop over IDs
    for i in range(len(ids)):
        name = ids[i]
        textoutfile = 'text/'+name+'_text.txt'
        if (os.path.exists(textoutfile)==False and os.path.exists(textoutfile+'.gz')==False) or clobber:
            # Get 
            text = gettext(name,method='html')
            if text is None:
                text = gettext(name,method='pdf')
            if text is None:
                text = gettext(name,method='source')
            if text is None:
                print(i+1,name)
                continue
            # Write text to file
            with open(textoutfile,'w') as f:
                f.write(text)
            r = subprocess.run(['gzip',textoutfile],shell=False,capture_output=True)
            res = searchtext(text)
            # Write search to file
            outsearchfile = 'search/'+name+'_search.json'
            with open(outsearchfile, 'w') as f: 
                f.write(json.dumps(res))
            py = (res['python'] or res['numpy'] or res['scipy'] or
                  res['astropy'] or res['sklearn'])
            jl = res['julia']
            print(i+1,name,py,jl)
