import json,math,struct,wave,io,re
from playwright.sync_api import sync_playwright
import os
URL="file://"+os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","index.html")
buf=io.BytesIO();w=wave.open(buf,"wb");w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b"".join(struct.pack("<h",int(8000*math.sin(i/6))) for i in range(2400)));w.close();WAV=buf.getvalue()
R=[];ERR=[]
def chk(n,c,i=""):
    R.append(bool(c))
    if not c: print("FAIL:",n,i)
INIT="""
window.__spoken=[];window.__aud=[];window.__rec=0;window.__V=[{lang:'en-US',name:'Sam'},{lang:'en-GB',name:'Dan'}];window.__heard=['lantern'];window.__recMode='ok';
Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>window.__V,speak(u){window.__spoken.push({t:u.text,lang:u.lang,v:u.voice&&u.voice.lang,rate:u.rate});setTimeout(()=>u.onend&&u.onend(),400)},cancel(){},addEventListener(){}}});
window.SpeechSynthesisUtterance=function(t){this.text=t};
const A=window.Audio;window.Audio=function(u){const a=new A(u);window.__aud.push({url:u,a,err:false});a.addEventListener('error',()=>{});return a};
window.SpeechRecognition=function(){this.start=()=>{window.__rec++;setTimeout(()=>{if(window.__recMode==='deny'){this.onerror&&this.onerror({error:'not-allowed'});return}this.onresult({results:[window.__heard.map(t=>({transcript:t}))]});this.onend&&this.onend()},60)}};
"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"]);pg=b.new_context(viewport={"width":1280,"height":900}).new_page()
    pg.add_init_script(INIT)
    pg.on("console",lambda m:ERR.append(m.text) if m.type=="error" and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    pg.on("pageerror",lambda e:ERR.append("PAGEERROR "+str(e)))
    def dictroute(r):
        u=r.request.url
        if u.endswith("/lantern"):r.fulfill(json=[{"word":"lantern","phonetic":"/ˈlæn.tən/","phonetics":[{"text":"/ˈlæn.tən/","audio":"https://audio.test/lantern-uk.mp3"},{"text":"/ˈlæn.tɚn/","audio":"https://audio.test/lantern-us.mp3"}]}])
        elif u.endswith("/offline"):r.abort()
        else:r.fulfill(status=404,json={"title":"No Definitions Found"})
    pg.route("https://api.dictionaryapi.dev/**",dictroute)
    pg.route("https://audio.test/**",lambda r:r.fulfill(status=404) if "bad" in r.request.url else r.fulfill(body=WAV,content_type="audio/wav"))
    pg.goto(URL);pg.wait_for_timeout(300);ev=pg.evaluate;ls=lambda k:json.loads(ev("k=>localStorage.getItem(k)",k) or "null")
    go=lambda h:(ev("h=>location.hash=h",h),pg.wait_for_timeout(120))
    go("#library")
    def add(term,pos="noun",d="A test definition here.",ex="",mine="",ipa="",lookup=False,ipauk="",syl="",stress=""):
        pg.click('#vLib .libhead [data-act=add]');pg.fill("#f_term",term);pg.click("[data-act=manual]");pg.select_option("#f_pos",pos);pg.fill("#f_def",d);pg.fill("#f_ex",ex);pg.fill("#f_mine",mine)
        if not ev("document.getElementById('pdet').open"):pg.click("#pdet summary")
        if ipa:pg.fill("#f_pron",ipa)
        if ipauk:pg.fill("#f_ipaUK",ipauk)
        if syl:pg.fill("#f_syl",syl)
        if stress:pg.fill("#f_stress",stress)
        if lookup:pg.click("[data-act=flook]");pg.wait_for_timeout(300)
        return pg.inner_text("#plmsg")
    def save(): pg.click("#save");pg.wait_for_timeout(100)
    W=lambda t:[w for w in ls("ww.words.v1") if w["term"]==t][0]
    # 1 lookup success fills + stores
    m=add("lantern",ex="She carried a lantern home.",mine="My lantern glows.",lookup=True)
    chk("lookup fills IPA + audio",pg.input_value("#f_ipaUK")=="/ˈlæn.tən/" and pg.input_value("#f_ipaUS")=="/ˈlæn.tɚn/" and "Filled" in m,m)
    save();L=W("lantern");chk("pronunciation stored with entry",L["ipaUK"]=="/ˈlæn.tən/" and L["audioUS"].endswith("lantern-us.mp3") and L["audioUK"].endswith("lantern-uk.mp3"))
    # 2 recorded audio plays, both accents
    pg.click('#cards details.dict summary');
    pg.click('.prow .spk[data-a=uk]');pg.wait_for_timeout(120);chk("button animates while playing",pg.locator(".prow .spk[data-a=uk].playing").count()==1)
    pg.wait_for_timeout(900);u=ev("__aud.map(a=>a.url)");chk("UK recorded audio requested",u and u[-1].endswith("lantern-uk.mp3"),str(u))
    played=ev("(()=>{const a=__aud[__aud.length-1].a;return [a.ended||a.currentTime>0, a.error&&a.error.code]})()");chk("recorded audio actually played",played[0] and not played[1],str(played))
    chk("animation stops after playback",pg.locator(".spk.playing").count()==0)
    pg.click('.prow .spk[data-a=us]');pg.wait_for_timeout(500);chk("US recorded audio selected",ev("__aud.at(-1).url").endswith("lantern-us.mp3"))
    n=ev("__aud.length");pg.click('[data-act=replay]');pg.wait_for_timeout(300);chk("replay plays again",ev("__aud.length")==n+1 and ev("__aud.at(-1).url").endswith("lantern-us.mp3"))
    # derived info
    t=pg.inner_text("#cards details.dict");chk("syllables/stress/spelling from IPA","2 syllables, stress on the 1st" in t and "LAN-tuhn" in t and "/ˈlæn.tən/" in t,t[:300])
    # 3 TTS fallback, accents -> voices
    ms=add("hush",d="A sudden quiet.",ex="A hush fell over the room.",ipa="/hʌʃ/",lookup=True)
    chk("missing dictionary entry handled",("no entry" in ms) and pg.input_value("#f_pron")=="/hʌʃ/",ms);save()
    chk("no fake audio saved for missing entry",W("hush")["audioUK"]=="" and W("hush")["ipaUK"]=="")
    card=lambda t:pg.locator("#cards .wcard",has=pg.locator("h3",has_text=t))
    card("hush").locator("summary").click();card("hush").locator('.prow .spk[data-a=uk]').click();pg.wait_for_timeout(100);s=ev("__spoken.at(-1)")
    chk("TTS fallback uses British voice",s["t"]=="hush" and s["lang"]=="en-GB" and s["v"]=="en-GB",str(s))
    card("hush").locator('.prow .spk[data-a=us]').click();pg.wait_for_timeout(100);s=ev("__spoken.at(-1)");chk("TTS fallback uses American voice",s["lang"]=="en-US" and s["v"]=="en-US",str(s))
    # default accent switch + sentence audio
    pg.click('#vsw [data-act=acc][data-a=us]');chk("default accent saved",ls("ww.set.v1")["accent"]=="us")
    card("hush").locator("p.q .spk").first.click();pg.wait_for_timeout(100);s=ev("__spoken.at(-1)");chk("example sentence audio, chosen accent",s["t"]=="A hush fell over the room." and s["v"]=="en-US",str(s))
    card("hush").locator("h3 .spk").click();pg.wait_for_timeout(100);chk("headword speaker follows default accent",ev("__spoken.at(-1).v")=="en-US")
    pg.click('#vsw [data-act=acc][data-a=uk]');card("hush").locator("h3 .spk").click();pg.wait_for_timeout(100);chk("switching back to British works",ev("__spoken.at(-1).v")=="en-GB")
    pg.click('#vsw [data-act=slow]');card("hush").locator("h3 .spk").click();pg.wait_for_timeout(100);chk("slow mode lowers speech rate",ev("__spoken.at(-1).rate")<0.8);pg.click('#vsw [data-act=slow]')
    # no matching voice
    ev("window.__V=[]");card("hush").locator("h3 .spk").click();pg.wait_for_timeout(150);chk("no-voice device: still speaks + tells the user",ev("__spoken.at(-1).v")is None and ev("__spoken.at(-1).lang")=="en-GB" and "British voice" in pg.inner_text("#toast"));ev("window.__V=[{lang:'en-US',name:'Sam'},{lang:'en-GB',name:'Dan'}]")
    # broken audio URL falls back to TTS
    add("bad",d="Audio link is broken.");pg.evaluate("document.querySelector('[name=audioUK]').value='https://audio.test/bad-uk.mp3'");save()
    k=ev("__spoken.length");card("bad").locator("summary").click();card("bad").locator('.prow .spk[data-a=uk]').click();pg.wait_for_timeout(700);chk("broken audio falls back to device voice",ev("__spoken.length")==k+1 and ev("__spoken.at(-1).t")=="bad")
    # offline lookup
    mo=add("offline",d="Pretend offline test.",lookup=True);chk("unreachable dictionary handled gracefully","can’t be reached" in mo,mo);pg.click("#dlg [data-act=close]")
    # validation + manual override
    add("manual",d="Manual entry test.",ipa="/ˈmæn.ju.əl/",syl="2",stress="5");pg.click("#save");chk("stress > syllables rejected","From 1" in pg.inner_text("#e_stress"));pg.fill("#f_stress","2");save()
    card("manual").locator("summary").click();chk("manual syllable/stress overrides IPA",("2 syllables, stress on the 2nd" in card("manual").inner_text()))
    # 4 practice
    card("lantern").evaluate("c=>c.querySelector('.dict').open=true");card("lantern").locator('[data-act=prac]').click();chk("practice dialog opens",ev("document.getElementById('dpr').open") and "lantern" in pg.inner_text("#prbody"))
    pg.click("[data-act=recask]");pg.wait_for_timeout(100);chk("microphone permission explained before recording",ev("__rec")==0 and "microphone" in pg.inner_text("#prbody"))
    pg.click("[data-act=recgo]");pg.wait_for_timeout(300);chk("recognized word compared (match)","matches" in pg.inner_text("#prmsg") and ev("__rec")==1)
    ev("window.__heard=['banter','lancer']");pg.click("[data-act=recask]");pg.click("[data-act=recgo]");pg.wait_for_timeout(300);chk("mismatch reported","isn’t quite" in pg.inner_text("#prmsg"))
    ev("window.__recMode='deny'");pg.click("[data-act=recask]");pg.click("[data-act=recgo]");pg.wait_for_timeout(300);chk("mic denied handled","isn’t available" in pg.inner_text("#prmsg"));ev("window.__recMode='ok'")
    pg.click("[data-act=pdone]");pg.wait_for_timeout(100);P=W("lantern")["pr"];chk("practice progress saved",P["done"] and P["n"]==1 and P["tries"]==2 and P["hits"]==1,str(P))
    pg.click("[data-act=pnext]");chk("next word",pg.locator("#prbody .hw").inner_text().split()[0]!="lantern");pg.click("#dpr [data-act=close]")
    pg.reload();pg.wait_for_timeout(300);go("#library");chk("practice + pronunciation persist after reload",W("lantern")["pr"]["n"]==1 and "Practiced 1 time" in (card("lantern").locator("summary").click() or card("lantern").inner_text()))
    go("#study");chk("study page shows practice progress","1 of" in pg.inner_text("#stbody") and "practiced aloud" in pg.inner_text("#stbody"))
    # 5 Memory Lane flashcard + feedback speakers
    got=False;fbok=False
    for i in range(60):
        ev("S={mode:'home'};renderStudy()");pg.click('#stbody [data-act=start][data-n="5"]')
        if ev("S.q.t")=="flash":
            got=True
            if fbok:break
        elif not fbok:
            q=ev("S.q");pg.click(f'.opt[data-i="{q["o"].index(q["a"])}"]');fbok=pg.locator("#fb .mini .spk").count()>=1
        if got and fbok:break
    chk("answer feedback card has speaker",fbok)
    if got:
        ev("S={mode:'home'};renderStudy()")
        for i in range(60):
            pg.click('#stbody [data-act=start][data-n="5"]')
            if ev("S.q.t")=="flash":break
            ev("S={mode:'home'};renderStudy()")
    chk("flashcard has speaker + accent switch",got and pg.locator(".pbar .spk").count()==1 and pg.locator(".pbar .seg").count()==1)
    if got:
        pg.click(".pbar .spk");pg.wait_for_timeout(100);chk("flashcard speaker speaks the saved word",ev("(__spoken.length&&__spoken.at(-1).t===S.w.term)||(__aud.length&&__aud.at(-1).url.includes(S.w.term))"));chk("flashcard still flips",(pg.click("#stbody .flip") or True) and pg.locator('.flip[aria-pressed=true]').count()==1)
    # 6 existing data intact + mobile
    chk("existing review fields intact",all(k in W("lantern") for k in ["box","ok","bad","due","mastered","fav"]))
    for wd in (390,320):
        pg.set_viewport_size({"width":wd,"height":800})
        for h in ["#library","#study","#garden"]:
            go(h);chk(f"no h-scroll {wd} {h}",ev("document.documentElement.scrollWidth-innerWidth")<=1,str(ev("document.documentElement.scrollWidth-innerWidth")))
        go("#library");card("lantern").locator("summary").click() if not ev("document.querySelector('.dict[open]')") else None;chk(f"details open no h-scroll {wd}",ev("document.documentElement.scrollWidth-innerWidth")<=1)
        pg.click('#vLib .libhead [data-act=add]');pg.click("[data-act=manual]");pg.click("#pdet summary");chk(f"form pronunciation block fits {wd}",ev("document.getElementById('dlg').scrollWidth<=document.getElementById('dlg').clientWidth+1"));pg.screenshot(path=f"s_form{wd}.png");pg.click("#dlg [data-act=close]")
        card("lantern").evaluate("c=>c.querySelector('.dict').open=true");card("lantern").locator('[data-act=prac]').click();chk(f"practice dialog fits {wd}",ev("(()=>{var r=document.getElementById('dpr').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1})()"));pg.screenshot(path=f"s_prac{wd}.png");pg.click("#dpr [data-act=close]")
    pg.set_viewport_size({"width":1280,"height":900});go("#library");pg.evaluate("document.querySelectorAll('.dict').forEach(d=>d.open=true)");pg.wait_for_timeout(200);pg.screenshot(path="/tmp/s_dict.png",clip={"x":280,"y":0,"width":1000,"height":900})
    b.close()
print("\n%d checks, %d failed"%(len(R),R.count(False)));print("console/page errors:",ERR[:6])
