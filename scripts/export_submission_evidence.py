from pathlib import Path
import subprocess,json,hashlib,datetime,shutil
root=Path(__file__).resolve().parents[1];base=root/'evidence/phase2/pcaps';exp=root/'evidence/phase2/exports';exp.mkdir(exist_ok=True)
t='/Applications/Wireshark.app/Contents/MacOS/tshark';cap=base/'dns-tcp-tls.pcapng'
fields=['frame.number','frame.time','ip.src','ip.dst','udp.srcport','udp.dstport','dns.id','dns.flags.response','dns.qry.name','dns.response_to','dns.a','dns.resp.ttl']
cmd=[t,'-n','-r',str(cap),'-Y','frame.number == 16 || frame.number == 17','-T','fields','-E','header=y']
for f in fields:cmd+=['-e',f]
r=subprocess.run(cmd,capture_output=True,text=True,check=True)
(base/'01-dns-query-response.tsv').write_text(r.stdout)
rows=r.stdout.strip().splitlines();records=[dict(zip(fields,row.split('\t'))) for row in rows[1:]]
assert records[0]['dns.id']==records[1]['dns.id']=='0x1a47'
assert records[1]['dns.response_to']=='16' and records[1]['dns.a']=='10.7.7.242'
text='GENUINE TSHARK PACKET EXPORT - NOT A WIRESHARK UI SCREENSHOT\nSource: evidence/phase2/pcaps/dns-tcp-tls.pcapng\nSHA-256: '+hashlib.sha256(cap.read_bytes()).hexdigest()+'\nFilter: frame.number == 16 || frame.number == 17\n\n'
for row in records:
 text+='\n'.join(f'{k}: {row.get(k, "")}' for k in fields)+'\n\n'
text+='Matching query/response: transaction 0x1a47; response frame 17 identifies query frame 16.\n'
(base/'01-dns-query-response.txt').write_text(text)
# Real textual exports indexed by purpose, copied byte-for-byte from actual logs.
selected={'dns-resolution':'20261124-150613-143356-test.txt','tls-verification':'20261124-145548-586670-tls.txt','https-headers':'20261124-151049-397414-test.txt','load-balancing':'20261124-151052-325065-test.txt','etag-304-caching':'20261124-151055-241606-test.txt','firewall-isolation-current-ip':'20261124-162147-295750-test.txt','backend-failover-recovery':'20261124-151627-955479-demo.txt','dns-failover':'20261124-151533-343105-test.txt','ttl-migration-observer':'20261124-152552-400567-observe.txt','standby-migration':'20261124-152750-651619-test.txt','migration-rollback':'20261124-152941-791907-test.txt','pf-rollback':'20261124-161551-165339-firewall.txt','latest-acceptance-FAIL':'20261124-165637-991096-test.txt'}
provenance={}
for label,name in selected.items():
 src=root/'evidence/phase2/runs'/name;dst=exp/(label+'.txt');shutil.copy2(src,dst)
 provenance[dst.name]={'source':str(src.relative_to(root)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'copy':'byte-for-byte genuine command output'}
(exp/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
# Revalidate captures without modifying them.
audit={'observed_at':datetime.datetime.now().astimezone().isoformat(),'captures':{}}
for p in [cap,base/'dns-tcp-tls.pcap']:
 cr=subprocess.run(['/Applications/Wireshark.app/Contents/MacOS/capinfos',str(p)],capture_output=True,text=True)
 tr=subprocess.run([t,'-n','-r',str(p),'-d','tcp.port==8443,tls','-Y','dns.qry.name == "app.codexers.test" || tcp.port == 8443','-T','fields','-e','frame.number','-e','tcp.stream','-e','dns.response_to','-e','tls.handshake.type'],capture_output=True,text=True)
 audit['captures'][p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'capinfos_exit':cr.returncode,'capinfos':cr.stdout,'capinfos_error':cr.stderr,'tshark_exit':tr.returncode,'tshark_error':tr.stderr}
(base/'final-qa-verification.json').write_text(json.dumps(audit,indent=2)+'\n')
