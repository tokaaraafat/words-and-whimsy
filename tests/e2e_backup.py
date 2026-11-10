import json,datetime,os,re,tempfile
from playwright.sync_api import sync_playwright
import os
URL="file://"+os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","index.html")
R=[];ERR=[];TMP=tempfile.mkdtemp()
def chk(n,c,i=""):
    R.append(bool(c))
    if not c: print("FAIL:",n,i)
UTC=datetime.timezone.utc;NOW=datetime.datetime.now(UTC)
def iso(d):return d.isoformat(timespec="milliseconds").replace("+00:00","Z")
def at(n,h=12):return NOW.replace(hour=h,minute=0,second=0,microsecond=0)-datetime.timedelta(days=n)
def word(i,t,**o):
    d=dict(id=f"w{i}",term=t,pos="noun",**{"def":f"Meaning of {t} here."},ar="",syn=["alpha"],ant=[],ex=f"A sentence with {t} in it.",mine="",pron="",fav=False,mastered=False,added=iso(at(5)),updated=iso(at(5)),box=0,ok=0,bad=0,last="",due=iso(at(5)),ipaUK="",ipaUS="",resp="",audioUK="",audioUS="",syl=0,stress=0,pr={});d.update(o);return d
def seed(words=(),hist=(),journal=()):
    return "if(!localStorage.getItem('__seeded')){localStorage.setItem('__seeded','1');localStorage.setItem('ww.words.v1',%s);localStorage.setItem('ww.hist.v1',%s);localStorage.setItem('ww.journal.v1',%s)}"%tuple(json.dumps(json.dumps(x)) for x in (list(words),list(hist),list(journal)))
MODES={"dl":"window.claude={use:async n=>n==='downloads'?{save:async({filename,data})=>{window.__saved={filename,data}}}:null};",
"decline":"window.claude={use:async n=>n==='downloads'?{save:async()=>{throw {code:'declined',message:'no'}}}:null};",
"nocap":"window.claude={use:async n=>null};","none":""}
def mk(b,mode,sd=""):
    ctx=b.new_context(viewport={"width":1280,"height":900},accept_downloads=True);ctx.grant_permissions(["clipboard-read","clipboard-write"]);pg=ctx.new_page()
    pg.add_init_script(MODES[mode]+sd)
    pg.on("console",lambda m:ERR.append(m.text) if m.type=="error" and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    pg.on("pageerror",lambda e:ERR.append("PAGEERROR "+str(e)))
    pg.goto(URL);pg.wait_for_timeout(300);return pg
def jv(pg,k):return json.loads(pg.evaluate("k=>localStorage.getItem(k)",k) or "null")
def go(pg,h):pg.evaluate("h=>location.hash=h",h);pg.wait_for_timeout(150)
def hist(w,n,r="good"):return {"w":w,"t":iso(at(n,15)),"k":"flash","r":r}
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---- STREAK: sidebar must equal Passport and follow activity (words, reviews, pages)
    def streaks(words,hs,js):
        pg=mk(b,"none",seed(words,hs,js));side=pg.inner_text("#streakN");lab=pg.inner_text(".streak span");go(pg,"#passport");ps=pg.locator("#passb .note",has_text="Learning streak").locator(".qp").inner_text();pg.context.close();return side,ps,lab
    old=[word(1,"alpha",added=iso(at(3)),updated=iso(at(3)))]
    cases=[("review today, words only 3 days ago",old,[hist("w1",0)],[],1),("reviews today, yesterday, 2 days ago + word added 3 days ago",old,[hist("w1",0),hist("w1",1),hist("w1",2)],[],4),("only yesterday",old,[hist("w1",1)],[],1),("page written today",old,[],[{"id":"j","date":NOW.strftime("%Y-%m-%d"),"title":"","body":"hello there","prompt":"","created":iso(at(0)),"updated":iso(at(0))}],1),("nothing recent",old,[],[],0),("gap breaks streak",old,[hist("w1",0),hist("w1",3)],[],1)]
    for name,ws,hs,js,exp in cases:
        s,ps,lab=streaks(ws,hs,js);n=lambda t:int(t.split()[0]);chk(f"streak: {name}: sidebar == Passport == {exp}",n(s)==n(ps)==exp,f"{s} / {ps}")
    chk("sidebar label describes learning, not only adding words",lab=="of learning in a row",lab)
    # ---- fixture data
    W=[word(i,t,fav=i==1,mastered=i==2,box=i,ok=i*2,bad=i%2,updated=iso(at(2)),added=iso(at(6-i))) for i,t in enumerate(["alpha","bravo","charlie","delta"],1)]
    H=[hist("w1",2),hist("w2",1,"bad"),hist("w3",0,"hard")];Jn=[{"id":"j1","date":NOW.strftime("%Y-%m-%d"),"title":"Notes","body":"alpha and bravo together","prompt":"","created":iso(at(0)),"updated":iso(at(0))}]
    # ---- EXPORT with downloads capability
    pg=mk(b,"dl",seed(W,H,Jn));go(pg,"#passport")
    chk("status before any backup","haven’t made a backup" in pg.inner_text("#bkst"))
    pg.click("[data-act=bkexp]");pg.wait_for_function("window.__saved",timeout=3000);sv=pg.evaluate("window.__saved");d=json.loads(sv["data"])
    chk("file name is dated .json",re.fullmatch(r"words-and-whimsy-backup-\d{4}-\d{2}-\d{2}\.json",sv["filename"]),sv["filename"])
    chk("file holds all saved data, exactly",d["app"]=="words-and-whimsy" and d["version"]==1 and d["words"]==jv(pg,"ww.words.v1") and d["history"]==jv(pg,"ww.hist.v1") and d["journal"]==jv(pg,"ww.journal.v1") and len(d["words"])==4)
    pg.wait_for_timeout(150);chk("status: backed up + timestamp saved","Everything is backed up" in pg.inner_text("#bkst") and jv(pg,"ww.set.v1")["lastBackup"] and "saved as" in pg.inner_text("#bkmsg"),pg.inner_text("#bkst"))
    go(pg,"#library");pg.click('button[aria-label="Favorite alpha"]');go(pg,"#passport");chk("status warns about changes since the backup","changes since" in pg.inner_text("#bkst"),pg.inner_text("#bkst"))
    export_json=sv["data"];exp_path=os.path.join(TMP,"b.json");open(exp_path,"w",encoding="utf8").write(export_json)
    # ---- declined / unavailable / no-claude paths
    pg2=mk(b,"decline",seed(W,H,Jn));go(pg2,"#passport");pg2.click("[data-act=bkexp]");pg2.wait_for_timeout(300)
    chk("declined save: clear message, not marked as backed up","declined" in pg2.inner_text("#bkmsg") and not (jv(pg2,"ww.set.v1") or {}).get("lastBackup") and "haven’t made" in pg2.inner_text("#bkst"))
    pg3=mk(b,"nocap",seed(W,H,Jn));go(pg3,"#passport");pg3.click("[data-act=bkexp]");pg3.wait_for_timeout(300)
    t=pg3.input_value("#bktext");chk("no file-saving here: backup text offered instead",pg3.locator("#bkbox").is_visible() and json.loads(t)["words"]==jv(pg3,"ww.words.v1") and "Copy the text" in pg3.inner_text("#bkmsg") and not (jv(pg3,"ww.set.v1") or {}).get("lastBackup"))
    pg3.click("[data-act=bkcopy]");pg3.wait_for_timeout(300);chk("copying counts as backing up, clipboard has the data",json.loads(pg3.evaluate("navigator.clipboard.readText()"))["words"]==json.loads(t)["words"] and "Everything is backed up" in pg3.inner_text("#bkst"))
    pg4=mk(b,"none",seed(W,H,Jn));go(pg4,"#passport")
    with pg4.expect_download(timeout=4000) as dl:pg4.click("[data-act=bkexp]")
    f=dl.value;pth=f.path();chk("outside Claude: normal file download",re.match(r"words-and-whimsy-backup-.*\.json",f.suggested_filename) and json.load(open(pth,encoding="utf8"))["words"]==jv(pg4,"ww.words.v1") and "downloaded" in pg4.inner_text("#bkmsg"))
    # ---- RESTORE into an empty browser (also proves the export is a real backup)
    pg5=mk(b,"dl");go(pg5,"#passport");pg5.set_input_files("#bkfile",exp_path);pg5.wait_for_function("document.getElementById('bkgo')&&!document.getElementById('bkgo').hidden",timeout=3000)
    m=pg5.inner_text("#bkmsg");chk("preview explains what will happen, changes nothing yet","4 words" in m and "add 4 new words" in m and "Nothing is deleted" in m and jv(pg5,"ww.words.v1") is None,m)
    pg5.click("[data-act=bkno]");chk("cancel leaves data untouched",jv(pg5,"ww.words.v1") is None and pg5.locator("#bkgo").is_hidden())
    pg5.set_input_files("#bkfile",exp_path);pg5.wait_for_function("!document.getElementById('bkgo').hidden");pg5.click("[data-act=bkgo]");pg5.wait_for_timeout(200)
    chk("restore recreates words, reviews and pages exactly",jv(pg5,"ww.words.v1")==json.loads(export_json)["words"] and jv(pg5,"ww.hist.v1")==json.loads(export_json)["history"] and jv(pg5,"ww.journal.v1")==json.loads(export_json)["journal"])
    go(pg5,"#library");chk("library shows restored words",pg5.locator("#cards .wcard").count()==4);go(pg5,"#garden");chk("garden shows restored words (1 bloom)",pg5.locator("#beds .fl").count()==4 and pg5.locator("#beds .fl.bloom").count()==1)
    go(pg5,"#desk");chk("restored journal page present","Notes" in pg5.inner_text("#jlist"))
    pg5.reload();pg5.wait_for_timeout(300);chk("restored data survives reload",len(jv(pg5,"ww.words.v1"))==4 and len(jv(pg5,"ww.hist.v1"))==3)
    # ---- MERGE into existing data
    cur=[word(1,"alpha",updated=iso(at(4)),**{"def":"Old alpha meaning here."}),word(2,"bravo",updated=iso(at(1)),**{"def":"Recent bravo edit here."}),word(3,"charlie")]
    inc={"app":"words-and-whimsy","version":1,"exported":iso(at(0)),"words":[word(1,"alpha",updated=iso(at(1)),**{"def":"Newer alpha meaning here."}),word(2,"bravo",updated=iso(at(5)),**{"def":"Stale bravo copy here."}),word(9,"echo"),word(77,"CHARLIE")],"history":[hist("w9",1),hist("w77",1,"bad"),hist("w1",2)],"journal":[]}
    mp=os.path.join(TMP,"m.json");open(mp,"w",encoding="utf8").write(json.dumps(inc))
    pg6=mk(b,"dl",seed(cur,[hist("w1",2)],[]));go(pg6,"#passport");pg6.set_input_files("#bkfile",mp);pg6.wait_for_function("!document.getElementById('bkgo').hidden");m=pg6.inner_text("#bkmsg")
    chk("merge preview counts","add 1 new words" in m and "update 1 with newer" in m and "add 2 reviews" in m and "1 already exist" in m,m)
    pg6.click("[data-act=bkgo]");pg6.wait_for_timeout(200);Wn={w["term"]:w for w in jv(pg6,"ww.words.v1")};Hn=jv(pg6,"ww.hist.v1")
    chk("merge: newer wins, stale ignored, new added, same-term not duplicated",len(Wn)==4 and Wn["alpha"]["def"].startswith("Newer") and Wn["bravo"]["def"].startswith("Recent") and "echo" in Wn and "CHARLIE" not in Wn)
    chk("merge: reviews added once, duplicate's review re-pointed to existing word",len(Hn)==3 and any(e["w"]=="w3" and e["r"]=="bad" for e in Hn) and not any(e["w"]=="w77" for e in Hn))
    # ---- invalid files and paste flow
    pg7=mk(b,"dl",seed(W,H,Jn));go(pg7,"#passport");before=jv(pg7,"ww.words.v1")
    for name,txt in [("not JSON","hello world"),("wrong app",'{"app":"other","version":1,"words":[]}'),("newer version",'{"app":"words-and-whimsy","version":9,"words":[]}'),("truncated",export_json[:200])]:
        fp=os.path.join(TMP,"bad.json");open(fp,"w",encoding="utf8").write(txt);pg7.set_input_files("#bkfile",fp);pg7.wait_for_timeout(250)
        chk(f"bad file ({name}) rejected with a message",pg7.locator("#bkgo").is_hidden() and pg7.locator("#bkmsg.bad").count()==1 and jv(pg7,"ww.words.v1")==before,pg7.inner_text("#bkmsg"))
    pg7.click("[data-act=bkbox]");chk("text box shows current backup",json.loads(pg7.input_value("#bktext"))["words"]==before)
    inc2=dict(inc);inc2["words"]=[word(50,"foxtrot")];inc2["history"]=[];pg7.fill("#bktext",json.dumps(inc2));pg7.click("[data-act=bkpv]");pg7.wait_for_timeout(100);chk("paste flow previews","add 1 new words" in pg7.inner_text("#bkmsg") and pg7.locator("#bkgo").is_visible())
    pg7.click("[data-act=bkgo]");pg7.wait_for_timeout(150);chk("paste flow restores",any(w["term"]=="foxtrot" for w in jv(pg7,"ww.words.v1")) and len(jv(pg7,"ww.words.v1"))==5)
    fp=os.path.join(TMP,"again.json");open(fp,"w",encoding="utf8").write(export_json);pg7.set_input_files("#bkfile",fp);pg7.wait_for_function("!document.getElementById('bkgo').hidden");pg7.click("[data-act=bkexp]");pg7.wait_for_timeout(300)
    chk("any other action disarms a pending restore",pg7.locator("#bkgo").is_hidden() and "Restore now" not in pg7.inner_text("#bkmsg"))
    # ---- mobile fit
    for wd in (390,320):
        pg7.set_viewport_size({"width":wd,"height":800});go(pg7,"#passport");pg7.click("[data-act=bkbox]");chk(f"backup card fits at {wd}",pg7.evaluate("document.documentElement.scrollWidth-innerWidth")<=1 and pg7.locator("[data-act=bkexp]").is_visible())
    b.close()
print("\n%d checks, %d failed"%(len(R),R.count(False)));print("console/page errors:",ERR[:6])
