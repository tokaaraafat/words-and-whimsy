import json,re,sys,datetime
from playwright.sync_api import sync_playwright
import os
URL="file://"+os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","index.html")
R=[];ERR=[]
def chk(n,c,i=""):
    R.append((n,bool(c),i));
    if not c: print("FAIL:",n,i)
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(viewport={"width":1280,"height":900});pg=ctx.new_page()
    pg.on("console",lambda m:ERR.append(m.text) if m.type=="error" and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    pg.on("pageerror",lambda e:ERR.append("PAGEERROR "+str(e)))
    pg.goto(URL);pg.wait_for_timeout(300)
    ev=pg.evaluate; ls=lambda k:json.loads(ev("k=>localStorage.getItem(k)",k) or "null")
    go=lambda h:(ev("h=>location.hash=h",h),pg.wait_for_timeout(120))
    vis=lambda s:ev("s=>{var e=document.querySelector(s);return !!e&&!e.hidden&&e.offsetParent!==null}",s)
    # 11 navigation
    for h,v in [("#home","#vHome"),("#library","#vLib"),("#garden","#vGarden"),("#study","#vStudy"),("#desk","#vDesk"),("#passport","#vPass"),("#pages","#vPages")]:
        pg.click(f'nav a[href="{h}"]');pg.wait_for_timeout(100)
        chk("nav "+h,vis(v) and ev("h=>document.querySelector('nav a[aria-current]').getAttribute('href')==h",h))
    go("#library")
    def add(term,pos,d,ar="",syn="",ant="",ex="",mine="",pron=""):
        pg.click('#vLib .libhead [data-act=add]');pg.fill("#f_term",term);pg.click("[data-act=manual]");pg.select_option("#f_pos",pos);pg.fill("#f_def",d);pg.fill("#f_syn",syn);pg.fill("#f_ant",ant);pg.fill("#f_ex",ex);pg.fill("#f_mine",mine);(pg.click("#pdet summary"),pg.fill("#f_pron",pron)) if pron else None;pg.click("#save");pg.wait_for_timeout(80)
    # validation
    pg.click('#vLib .libhead [data-act=add]');pg.click("[data-act=manual]");pg.click("#save")
    chk("empty form blocked",ev("document.getElementById('dlg').open") and "Enter" in pg.inner_text("#e_term") and pg.inner_text("#e_pos") and pg.inner_text("#e_def"))
    pg.fill("#f_term","lantern");pg.select_option("#f_pos","noun");pg.fill("#f_def","A portable case with a light inside.");pg.fill("#f_ex","She carried a lantern down the path.");pg.fill("#f_mine","The lantern glowed in the garden.");pg.fill("#f_syn","lamp, light");pg.fill("#f_ant","darkness");pg.click("#save");pg.wait_for_timeout(80)
    chk("add word",len(ls("ww.words.v1"))==1 and not ev("document.getElementById('dlg').open"))
    W=ls("ww.words.v1")[0];chk("date auto + fields",W["added"] and W["syn"]==["lamp","light"] and W["mastered"]==False)
    pg.click('#vLib .libhead [data-act=add]');pg.fill("#f_term","  LANTERN ");pg.click("[data-act=manual]") if pg.locator("#review").is_hidden() else None;pg.select_option("#f_pos","noun");pg.fill("#f_def","duplicate attempt");pg.click("#save")
    chk("duplicate detected",ev("document.getElementById('dlg').open") and "already" in pg.inner_text("#e_term") and len(ls("ww.words.v1"))==1);pg.click("#dlg [data-act=close]")
    for t,po,d,ar,s,a,e,m in [("hush","noun","A sudden quiet or stillness.","سكون","calm, quiet","noise","A hush fell over the room.","I loved the hush of morning."),("gleam","verb","To shine with a soft light.","يلمع","glow, shine","dull","Stars gleam above the sea.",""),("serene","adjective","Calm, peaceful, and untroubled.","هادئ","tranquil, calm","chaotic","The lake was serene at dawn.","She felt serene after the rain."),("gently","adverb","In a mild, kind way.","بلطف","softly","roughly","He gently closed the book.",""),("wander","verb","To walk without a fixed goal.","يتجول","roam, stroll","","They wander through old streets.","I like to wander by the river.")]:
        add(t,po,d,ar,s,a,e,m)
    chk("6 words saved",len(ls("ww.words.v1"))==6)
    # edit
    pg.click('button[aria-label="Edit hush"]');pg.fill("#f_def","A sudden, deep quiet or stillness.");pg.click("#save");pg.wait_for_timeout(80)
    chk("edit saves",[w for w in ls("ww.words.v1") if w["term"]=="hush"][0]["def"].startswith("A sudden, deep") and "deep quiet" in pg.inner_text("#cards"))
    pg.click('button[aria-label="Edit hush"]');pg.fill("#f_term","lantern");pg.click("#save");chk("rename onto duplicate blocked","already" in pg.inner_text("#e_term"));pg.click("#dlg [data-act=close]")
    # fav
    pg.click('button[aria-label="Favorite gleam"]');chk("favorite toggles",[w for w in ls("ww.words.v1") if w["term"]=="gleam"][0]["fav"])
    # delete
    add("temp","noun","A temporary word.");pg.click('button[aria-label="Delete temp"]');pg.click('[data-act=confirmdel]');pg.wait_for_timeout(80)
    chk("delete word",all(w["term"]!="temp" for w in ls("ww.words.v1")) and len(ls("ww.words.v1"))==6)
    # persistence
    pg.reload();pg.wait_for_timeout(300);go("#library");chk("persists after reload",len(ev("words"))==6 and pg.locator("#cards .wcard").count()==6)
    # 3 search
    def srch(q):
        pg.fill("#q",q);pg.wait_for_timeout(60);return sorted(x.inner_text() for x in pg.locator("#cards .wcard h3").all())
    chk("search term",srch("lan")==["lantern"]);chk("search ignores hidden Arabic",srch("هادئ")==[]);chk("search def",srch("light")==["gleam","lantern"] or srch("light")==["gleam","lantern"]);chk("search my sentence",srch("loved the hush")==["hush"]);chk("search none",pg.locator("#cards .none").count()==1 or srch("zzzz")==[]);srch("")
    # 4 filters/sort
    pg.select_option("#fpos","verb");chk("filter pos",sorted(x.inner_text() for x in pg.locator("#cards .wcard h3").all())==["gleam","wander"]);pg.select_option("#fpos","")
    pg.check("#ffav");chk("filter favorites",[x.inner_text() for x in pg.locator("#cards .wcard h3").all()]==["gleam"]);pg.uncheck("#ffav")
    for s,exp in [("az",["gently","gleam","hush","lantern","serene","wander"]),("za",["wander","serene","lantern","hush","gleam","gently"])]:
        pg.select_option("#fsort",s);chk("sort "+s,[x.inner_text() for x in pg.locator("#cards .wcard h3").all()]==exp)
    pg.select_option("#fsort","old");o=[x.inner_text() for x in pg.locator("#cards .wcard h3").all()];pg.select_option("#fsort","new");n=[x.inner_text() for x in pg.locator("#cards .wcard h3").all()]
    chk("sort old/new reverse",o==n[::-1] and o[0]=="lantern")
    pg.select_option("#fsort","fav");chk("sort favorites first",pg.locator("#cards .wcard h3").first.inner_text()=="gleam")
    # 5 garden
    go("#garden");chk("garden flower per word",pg.locator("#beds .fl").count()==6 and pg.locator("#beds .fl.bloom").count()==0)
    go("#library");pg.click('#cards [data-act=mast][data-id="'+[w for w in ls("ww.words.v1") if w["term"]=="serene"][0]["id"]+'"]');go("#garden")
    chk("garden bloom after mastering",pg.locator("#beds .fl.bloom").count()==1 and "serene" in pg.locator("#beds .fl.bloom").get_attribute("aria-label"))
    add_ok=True;go("#library");add("meadow","noun","A field of grass and flowers.");go("#garden");chk("garden grows with new word",pg.locator("#beds .fl").count()==7)
    pg.click("#beds .fl >> nth=0");chk("flower opens details",ev("document.getElementById('dview').open") and pg.locator("#vbody .wcard").count()==1)
    pg.click('#vbody [data-act=edit]');chk("edit from flower dialog",ev("document.getElementById('dlg').open") and not ev("document.getElementById('dview').open"));pg.click("#dlg [data-act=close]")
    go("#library");pg.click('button[aria-label="Delete meadow"]');pg.click('[data-act=confirmdel]');go("#garden");chk("garden shrinks on delete",pg.locator("#beds .fl").count()==6)
    # 6-8 memory lane
    go("#study");before={w["id"]:w for w in ls("ww.words.v1")};h0=len(ls("ww.hist.v1") or [])
    chk("study counts match",pg.inner_text("#stbody .stats").replace("\n"," ").split()[0]=="6")
    pg.click('#stbody [data-act=start][data-n="5"]');exp=[];terms={w["term"] for w in before.values()};i=0;flashok=True
    while ev("S.mode")=="run" and i<40:
        q=ev("S.q");w=ev("S.w");i+=1
        assert w["term"] in terms
        if q["t"]=="flash":
            r=["good","hard","bad"][i%3];pg.click("#stbody .flip");pg.click(f'[data-act=rate][data-r={r}]')
        else:
            ci=q["o"].index(q["a"]);ok=(i%3!=0);idx=ci if ok else [k for k in range(len(q["o"])) if k!=ci][0]
            chk("options valid "+q["t"],len(set(q["o"]))==len(q["o"]) and q["a"] in q["o"]);pg.click(f'.opt[data-i="{idx}"]');r="good" if ok else "bad"
            chk("feedback shown",pg.locator("#fb .fb").count()==1 and pg.locator(".opt.ok").count()==1);pg.click("[data-act=next]")
        exp.append((w["id"],r));pg.wait_for_timeout(40)
    chk("walk ends at summary",ev("S.mode")=="done" and "Walk complete" in pg.inner_text("#stbody"))
    H=ls("ww.hist.v1");chk("history saved",[(e["w"],e["r"]) for e in H[h0:]]==exp,str(len(H)-h0)+" vs "+str(len(exp)))
    g=sum(1 for _,r in exp if r=="good");hd=sum(1 for _,r in exp if r=="hard");bd=sum(1 for _,r in exp if r=="bad")
    chk("summary score matches",f"{len(exp)} time" in pg.inner_text("#stbody") and f"{g} easily, {hd} with effort, {bd} to try again" in pg.inner_text("#stbody"),pg.inner_text("#stbody")[:200])
    now={w["id"]:w for w in ls("ww.words.v1")};okp=True
    for wid,w0 in before.items():
        e=[r for i2,r in exp if i2==wid];box=w0["box"]
        for r in e:
            box=min(5,box+1) if r=="good" else box if r=="hard" else max(0,box-2)
        okp&=now[wid]["box"]==box and now[wid]["ok"]==w0["ok"]+sum(1 for r in e if r!="bad") and now[wid]["bad"]==w0["bad"]+sum(1 for r in e if r=="bad")
    chk("review progress math + saved",okp)
    pg.reload();pg.wait_for_timeout(300);chk("review progress persists",{w["id"]:(w["box"],w["ok"],w["bad"]) for w in ev("words")}=={k:(v["box"],v["ok"],v["bad"]) for k,v in now.items()} and len(ls("ww.hist.v1"))==len(H))
    # 9 writing
    go("#desk");pg.fill("#jtitle","Evening notes");pg.fill("#jbody","The ");pg.click("#jpick [data-t=lantern]");pg.type("#jbody"," gleamed, and the hush was serene.");pg.wait_for_timeout(60)
    chk("live used-words chips","lantern" in pg.inner_text("#jused") and "serene" in pg.inner_text("#jused") and "gleam" in pg.inner_text("#jused") and "hush" in pg.inner_text("#jused"),pg.inner_text("#jused"))
    pg.click("[data-act=jsave]");chk("entry saved",len(ls("ww.journal.v1"))==1 and "Evening notes" in pg.inner_text("#jlist"))
    pg.click("[data-act=jnew]");chk("new page clears",pg.input_value("#jbody")=="");pg.click("#jlist [data-act=jedit]");chk("entry reopens",pg.input_value("#jtitle")=="Evening notes" and "lantern" in pg.input_value("#jbody"))
    pg.fill("#jbody",pg.input_value("#jbody")+" Edited.");pg.click("[data-act=jsave]");chk("entry edit saved","Edited." in ls("ww.journal.v1")[0]["body"] and len(ls("ww.journal.v1"))==1)
    pg.click("[data-act=jnew]");pg.click("[data-act=jsave]");chk("empty page rejected",len(ls("ww.journal.v1"))==1)
    pg.reload();pg.wait_for_timeout(300);go("#desk");chk("entry persists",len(ev("J"))==1 and "Evening notes" in pg.inner_text("#jlist"))
    pg.click("#jlist [data-act=jdel]");chk("delete needs confirm",len(ls("ww.journal.v1"))==1);
    # 10 stats  (compare to independent calc)
    Wd=ls("ww.words.v1");Hh=ls("ww.hist.v1");Jj=ls("ww.journal.v1")
    def used(): 
        s=set()
        for e in Jj:
            for w in Wd:
                if re.search(r"\b"+re.escape(w["term"])+r"(?:s|es|d|ed|ing)?\b",e["title"]+" "+e["body"],re.I): s.add(w["id"])
        return len(s)
    go("#passport");vals=[int(x) for x in pg.locator("#passb .stat b").all_inner_texts()]
    chk("passport numbers",vals==[len(Wd),sum(1 for w in Wd if w["mastered"]),used(),len(Hh)],str(vals)+str([len(Wd),sum(1 for w in Wd if w["mastered"]),used(),len(Hh)]))
    go("#home");chk("home stats",[pg.inner_text("#sTotal"),pg.inner_text("#sFav"),pg.inner_text("#sMine")]==[str(len(Wd)),str(sum(1 for w in Wd if w["fav"])),str(sum(1 for w in Wd if w["mine"]))])
    today=datetime.date.today().isoformat();rv=sum(1 for e in Hh if e["t"][:10]==today)
    go("#passport");chk("goal ring text",f"{min(rv,10)}/10" in pg.inner_text("#passb") or f"{rv}/10" in pg.inner_text("#passb"))
    pg.select_option("#goal","5");chk("goal saved",ls("ww.set.v1")["goal"]==5 and f"{rv}/5" in pg.inner_text("#passb"))
    go("#pages");t=pg.inner_text("#pageb");chk("daily page records activity",f"{len(Hh)} review" in t.replace("1 reviews","1 review") or f"{rv} review" in t,t[:300])
    chk("daily page lists writing + words added","Evening notes" in t and "lantern" in t)
    pg.click('[data-act=pday][data-d="-1"]');chk("previous day opens (quiet)","quiet day" in pg.inner_text("#pageb") and pg.locator('[data-act=pday][data-d="1"]').is_enabled())
    pg.click('[data-act=pday][data-d="1"]');chk("returns to today","Evening notes" in pg.inner_text("#pageb"))
    pg.click('[data-act=jopen]');pg.wait_for_timeout(200);chk("open entry from day page",vis("#vDesk") and "Evening notes" in pg.input_value("#jtitle"))
    go("#home");bx=ev("[...document.querySelectorAll('.plan input')].map(b=>b.checked)");chk("home plan reflects real activity",bx==[rv>=5,True,True,True],str(bx)+" rv="+str(rv))
    pg.click("#shelf .stack >> nth=0");pg.wait_for_timeout(150);chk("shelf link filters library",vis("#vLib") and ev("F.pos")!="" and pg.locator("#cards .wcard").count()>=1);pg.select_option("#fpos","")
    # dark mode + home
    pg.click("#theme");chk("theme toggles",ev("document.documentElement.dataset.theme")=="dark");pg.click("#theme")
    # 14 dead buttons: static
    src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","index.html"),encoding="utf8").read()
    acts=set(re.findall(r'data-act="(\w+)"',src));handled=set(re.findall(r'a==="(\w+)"',src));chk("every data-act has a handler",not (acts-handled),str(acts-handled))
    chk("no dead # links",len(re.findall(r'href="#"',src))==0,str(len(re.findall(r'href="#"',src))))
    # 12 responsive
    for wd,hg in [(1280,900),(1024,800),(768,900),(390,800),(320,700)]:
        pg.set_viewport_size({"width":wd,"height":hg})
        for h in ["#home","#library","#garden","#study","#desk","#passport","#pages"]:
            go(h);ov=ev("document.documentElement.scrollWidth-window.innerWidth");chk(f"no h-scroll {wd} {h}",ov<=1,str(ov))
        if wd<=860:
            chk(f"bottom nav {wd}",ev("(()=>{var r=document.querySelector('nav').getBoundingClientRect();return Math.abs(r.bottom-innerHeight)<2})()"))
    pg.set_viewport_size({"width":1280,"height":900});go("#home");pg.wait_for_timeout(200);pg.screenshot(path="/tmp/s_home.png")
    go("#garden");pg.wait_for_timeout(300);pg.screenshot(path="/tmp/s_garden.png")
    pg.set_viewport_size({"width":390,"height":800});go("#library");pg.wait_for_timeout(200);pg.screenshot(path="/tmp/s_mob.png")
    b.close()
print("\n%d checks, %d failed"%(len(R),sum(1 for r in R if not r[1])));print("console/page errors:",ERR[:8])
