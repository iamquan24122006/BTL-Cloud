"""Verify direct ALB HTTPS, redirects, proxy URLs and secure Moodle cookies."""
from __future__ import annotations
import argparse,hashlib,hmac,json,socket,ssl,sys,time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit,urlencode
from urllib.request import HTTPRedirectHandler,build_opener,urlopen
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.acceptance.http_check import Client

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

class Assets(HTMLParser):
    def __init__(self,body):
        super().__init__(); self.urls=[]; self.feed(body.decode('utf-8',errors='replace'))
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        keys={'script':['src'],'img':['src'],'iframe':['src'],'source':['src'],'video':['src','poster'],'audio':['src'],'object':['data'],'form':['action']}.get(tag,[])
        if tag=='link' and any(t in a.get('rel','') for t in ('stylesheet','preload','icon')): keys=['href']
        for key in keys:
            if a.get(key): self.urls.append(a[key])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True); p.add_argument('--alb-dns',required=True)
    p.add_argument('--fixture',type=Path,required=True); p.add_argument('--admin-credentials',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); endpoint=urlsplit(a.url)
    assert endpoint.scheme=='https' and endpoint.hostname and not endpoint.query
    report={'started_unix':time.time(),'url':a.url,'checks':[]}
    def check(name,good):
        report['checks'].append({'name':name,'passed':bool(good)})
        print(name+': '+('PASS' if good else 'FAIL'),flush=True)
        if not good: raise RuntimeError(name)
    try:
        query='https://dns.google/resolve?'+urlencode({'name':endpoint.hostname,'type':'CNAME'})
        with urlopen(query,timeout=20) as r: dns=json.load(r)
        aliases=[x['data'].rstrip('.') for x in dns.get('Answer',[]) if x['type']==5]
        report['dns_cname']=aliases
        check('dns-points-directly-to-alb',a.alb_dns.rstrip('.') in aliases)
        context=ssl.create_default_context()
        with socket.create_connection((endpoint.hostname,443),timeout=15) as tcp:
            with context.wrap_socket(tcp,server_hostname=endpoint.hostname) as secure:
                cert=secure.getpeercert()
                report['tls']={'version':secure.version(),'cipher':secure.cipher()[0],
                    'subject_alt_names':cert.get('subjectAltName'),'issuer':cert.get('issuer'),
                    'not_before':cert.get('notBefore'),'not_after':cert.get('notAfter')}
                check('tls-chain-and-hostname-verified',True)
                check('tls-version-modern',secure.version() in ('TLSv1.2','TLSv1.3'))
        path='/login/index.php?med02_probe=redirect'
        try:
            response=build_opener(NoRedirect()).open('http://'+endpoint.hostname+path,timeout=20)
        except HTTPError as error: response=error
        with response:
            report['http_redirect']={'status':response.status,'location':response.headers.get('Location')}
            target=urlsplit(response.headers.get('Location','')); original=urlsplit(path)
            check('http-301-to-correct-https-url',response.status==301 and target.scheme=='https'
                  and target.hostname==endpoint.hostname and target.port in (None,443)
                  and target.path==original.path and target.query==original.query)
        with urlopen(a.url.rstrip('/')+'/login/index.php',timeout=30) as response:
            body=response.read(); location=response.url; headers=response.headers
            check('https-login-page-200',response.status==200)
            check('no-redirect-to-old-domain',location.startswith(a.url.rstrip('/')+'/'))
            check('hsts-present','max-age=' in headers.get('Strict-Transport-Security',''))
            check('login-page-no-http-assets-or-form',not any(u.startswith('http://') for u in Assets(body).urls))
        f=json.loads(a.fixture.read_text(encoding='utf-8')); admin=json.loads(a.admin_credentials.read_text(encoding='utf-8'))
        c=Client(a.url); username=f['users']['teacher']['username']
        password=hmac.new(admin['password'].encode(),username.encode(),hashlib.sha256).hexdigest()[:32]+'Aa7!'
        status,body,location=c.login(username,password)
        check('teacher-login-over-alb',status==200 and '/login/index.php' not in location)
        cookies=[cookie for cookie in c.cookies if cookie.name.startswith('MoodleSession')]
        check('session-cookie-secure',bool(cookies) and all(cookie.secure for cookie in cookies))
        check('session-cookie-httponly',all(cookie.has_nonstandard_attr('HttpOnly') for cookie in cookies))
        check('session-cookie-matches-new-host',all(cookie.domain.lstrip('.')==endpoint.hostname for cookie in cookies))
        for name,path in [('course','/course/view.php?id='+str(f['courses']['CLOUD-C01'])),('assignment','/mod/assign/view.php?id='+str(f['assignment']['cmid']))]:
            status,body,location=c.get(path)
            check(name+'-correct-https-host',status==200 and location.startswith(a.url.rstrip('/')+'/'))
            check(name+'-no-http-assets-or-form',not any(u.startswith('http://') for u in Assets(body).urls))
        report['status']='passed'
    except Exception as exc:
        report['status']='failed'; report['error']=type(exc).__name__+': '+str(exc)
        print('HTTPS check failed: '+str(exc),flush=True)
    finally:
        report['finished_unix']=time.time(); a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='passed' else 1

if __name__=='__main__': raise SystemExit(main())
