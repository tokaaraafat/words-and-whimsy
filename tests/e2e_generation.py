import json
from playwright.sync_api import sync_playwright
import os
URL="file://"+os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","index.html")
R=[];ERR=[]
def chk(n,c,i=""):
    R.append(bool(c))
    if not c: print("FAIL:",n,i)
INIT="""
window.__prompts=[];
const FX={serene:{pos:'adjective',definition:'Calm, peaceful, and not disturbed by anything.',synonyms:['calm','tranquil','peaceful','placid'],antonyms:['agitated','stormy'],example:'The lake looked serene in the early morning light.'},
 offline:{pos:'adjective',definition:'Not connected to the internet right now.',synonyms:['disconnected'],antonyms:['online'],example:'My phone was offline during the long train ride home.'},
 gleam:{pos:'verb',definition:'To shine softly with a clear light.',synonyms:['glow','shine'],antonyms:[],example:'The wet stones gleam under the street lamps at night.'},
 hush:{pos:'noun',definition:'A sudden quiet.',synonyms:['silence'],antonyms:['noise'],example:'A completely unrelated sentence appears here.'},
 zzqx:{error:'not_a_word'}};
window.__aiImpl=async inp=>{const w=inp.match(/English word “([^”]+)”/)[1];if(!FX[w])throw {code:'upstream_error',message:'x'};return FX[w]};
const sample=Object.assign(async()=>({text:'',truncated:false}),{json:async(i,o)=>{window.__prompts.push({i,o});return window.__aiImpl(i)},limits:async()=>({})});
window.claude={use:async n=>n==='sample'?sample:null};
"""
DICT_FAIL=[False]
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_context(viewport={"width":1280,"height":900}).new_page();pg.add_init_script(INIT)
    pg.on("console",lambda m:ERR.append(m.text) if m.type=="error" and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    pg.on("pageerror",lambda e:ERR.append("PAGEERROR "+str(e)))
    def dr(r):
        u=r.request.url;w=u.rsplit("/",1)[-1]
        if DICT_FAIL[0] or w=="offline":r.abort();return
        if w=="serene":r.fulfill(json=[{"word":"serene","phonetics":[{"text":"/sɪˈriːn/","audio":"https://audio.test/serene-uk.mp3"},{"text":"/sɪˈriːn/","audio":"https://audio.test/serene-us.mp3"}],"meanings":[{"partOfSpeech":"adjective","synonyms":["calm"],"antonyms":["stormy"],"definitions":[{"definition":"Calm and peaceful.","example":"A serene smile."}]}]}])
        elif w=="gleam":r.fulfill(json=[{"word":"gleam","phonetics":[{"text":"/ɡliːm/"}],"meanings":[{"partOfSpeech":"verb","synonyms":["glow","shine"],"antonyms":[],"definitions":[{"definition":"To shine with a soft light.","example":"The stars gleam above."}]}]}])
        else:r.fulfill(status=404,json={"title":"No Definitions Found"})
    pg.route("https://api.dictionaryapi.dev/**",dr);pg.route("https://audio.test/**",lambda r:r.fulfill(status=200,body=b"",content_type="audio/mpeg"))
    pg.goto(URL);pg.wait_for_timeout(400);ev=pg.evaluate;ls=lambda k:json.loads(ev("k=>localStorage.getItem(k)",k) or "null")
    ev("location.hash='#library'");W=lambda t:[w for w in ls("ww.words.v1") if w["term"]==t][0]
    opn=lambda:(pg.click('#vLib .libhead [data-act=add]'),pg.wait_for_timeout(50))
    def gen(t):
        pg.fill("#f_term",t);pg.click("#genbtn");pg.wait_for_function("!document.getElementById('genbtn').disabled",timeout=8000);pg.wait_for_timeout(80)
    # K/H: simplified form, no Arabic, validation
    opn();chk("no Arabic field anywhere in the form",pg.locator("#f_ar,[name=ar]").count()==0 and "arab" not in pg.inner_text("#wf").lower())
    chk("only the word is shown before generating",pg.locator("#review").is_hidden() and pg.locator("#save").is_hidden() and pg.locator("#genbtn").inner_text()=="Generate")
    pg.click("#genbtn");chk("empty word -> error, no AI call","Enter" in pg.inner_text("#e_term") and ev("__prompts.length")==0)
    pg.fill("#f_term","ab3");pg.click("#genbtn");chk("non-English text rejected before generating","English letters" in pg.inner_text("#e_term") and ev("__prompts.length")==0)
    # A: type word -> generate -> everything filled
    gen("serene");E=lambda n:pg.input_value(f"[name={n}]")
    chk("AI called once with the word, via quick tier",ev("__prompts.length")==1 and "“serene”" in ev("__prompts[0].i") and ev("__prompts[0].o.modelTier")=="quick")
    chk("definition/pos/synonyms/antonyms/example generated",E("pos")=="adjective" and "Calm, peaceful" in E("def") and E("syn")=="calm, tranquil, peaceful, placid" and E("ant")=="agitated, stormy" and "serene" in E("ex"),str([E("pos"),E("def"),E("syn"),E("ant"),E("ex")]))
    chk("IPA + audio come from the dictionary",E("ipaUK")=="/sɪˈriːn/" and E("ipaUS")=="/sɪˈriːn/" and E("pron")=="/sɪˈriːn/" and E("audioUK").endswith("serene-uk.mp3") and E("audioUS").endswith("serene-us.mp3"))
    st=pg.inner_text("#genst");chk("status shows both sources","written by Claude" in st and "Pronunciation found" in st,st)
    chk("review + save now visible, button becomes Regenerate",pg.locator("#review").is_visible() and pg.locator("#save").is_visible() and pg.locator("#genbtn").inner_text()=="Regenerate")
    pg.click("#save");pg.wait_for_timeout(100);S=W("serene")
    chk("saved complete entry in existing structure",S["pos"]=="adjective" and S["syn"]==["calm","tranquil","peaceful","placid"] and S["ant"]==["agitated","stormy"] and S["ipaUK"] and S["audioUS"] and S["ar"]=="" and S["mastered"]==False and S["box"]==0 and S["due"] and S["pr"]=={} and S["added"])
    t=pg.inner_text("#cards");chk("card shows English entry, no Arabic",pg.locator("#cards .ar").count()==0 and "Calm, peaceful" in t and "Similar:" in t and "Opposite:" in t)
    pg.click("#cards details.dict summary");t=pg.inner_text("#cards details.dict");chk("derived pronunciation info from real IPA","2 syllables, stress on the 2nd" in t and "sih-REEN" in t and "recorded audio" in t,t[:200])
    # G: duplicate before any AI call
    opn();n=ev("__prompts.length");pg.fill("#f_term","  SERENE ");pg.click("#genbtn");pg.wait_for_timeout(150)
    chk("duplicate caught before generating","already in your journal" in pg.inner_text("#e_term") and pg.locator("[data-act=editdup]").count()==1 and ev("__prompts.length")==n and pg.locator("#review").is_hidden())
    # I: Enter key generates
    pg.fill("#f_term","gleam");pg.press("#f_term","Enter");pg.wait_for_function("!document.getElementById('genbtn').disabled",timeout=8000);pg.wait_for_timeout(80)
    chk("Enter key generates",pg.locator("#review").is_visible() and E("def").startswith("To shine softly"))
    chk("dictionary IPA without audio: kept, audio empty, honest status",E("ipaUK")=="" and E("pron")=="/ɡliːm/" and E("audioUK")=="" and "No recorded audio" in pg.inner_text("#genst"))
    pg.click("#save");pg.wait_for_timeout(100)
    # C: dictionary unreachable, AI works
    opn();gen("offline");st=pg.inner_text("#genst")
    chk("pronunciation unavailable, entry still generated",E("def").startswith("Not connected") and "Pronunciation unavailable" in st and "can’t be reached" in st and E("ipaUK")=="" and E("ipaUS")=="" and E("pron")=="" and pg.input_value("[name=ipaUK]")=="" and pg.get_attribute("[name=pron]","placeholder")=="unavailable",st)
    pg.click("#save");pg.wait_for_timeout(100);O=W("offline");chk("no IPA/audio invented when lookup fails",O["pron"]=="" and O["ipaUK"]=="" and O["ipaUS"]=="" and O["audioUK"]=="" and O["syl"]==0)
    pg.click("#cards details.dict summary >> nth=0") if False else None
    card=lambda t:pg.locator("#cards .wcard",has=pg.locator("h3",has_text=t))
    card("offline").evaluate("c=>c.querySelector('.dict').open=true");t=card("offline").inner_text();chk("panel says unavailable",t.count("unavailable")>=3 and "device voice" in t,t[-300:])
    # D: AI denied -> dictionary entry
    ev("(()=>{window.__aiImpl=async()=>{throw {code:'not_granted',message:'no'}};return 1})()");ev("document.getElementById('dlg').close()") if False else None
    opn();DICT_FAIL[0]=False;gen("gleam") if False else None
    # (gleam exists, use serene-like new fixture via dictionary-only word)
    pg.click("#dlg [data-act=close]")
    # E/F: not a word, and both services failing
    ev("(()=>{window.__aiImpl=async inp=>({error:'not_a_word'});return 1})()");opn();gen("zzqx");chk("not-a-word message; no entry revealed","real English word" in pg.inner_text("#genst") and pg.locator("#review").is_hidden() and pg.locator("#manbtn").is_visible(),pg.inner_text("#genst"))
    pg.click("#manbtn");chk("manual path still available",pg.locator("#review").is_visible() and pg.locator("#save").is_visible());pg.select_option("#f_pos","noun");pg.fill("#f_def","A made-up test word here.");pg.click("#save");pg.wait_for_timeout(100);chk("manual entry saves",W("zzqx")["def"]=="A made-up test word here.")
    ev("(()=>{window.__aiImpl=async()=>{throw {code:'rate_limited',message:'slow'}};return 1})()");opn();gen("hush");st=pg.inner_text("#genst")
    chk("AI failure + no dictionary entry: clear message, manual fields shown","Too many requests" in st and "by hand" in st and pg.locator("#review").is_visible() and E("def")=="",st)
    pg.click("#dlg [data-act=close]")
    # D: AI not granted but dictionary has data -> fallback
    ev("(()=>{window.__aiImpl=async()=>{throw {code:'not_granted',message:'no'}};return 1})()");pg.click('#cards [data-act=del] >> nth=0') if False else None
    # delete 'gleam' so it can be regenerated through the dictionary fallback
    pg.click('button[aria-label="Delete gleam"]');pg.click("[data-act=confirmdel]");pg.wait_for_timeout(80)
    opn();gen("gleam");st=pg.inner_text("#genst")
    chk("AI declined -> dictionary text used and labelled","permission declined" in st and "dictionary’s entry" in st and E("def")=="To shine with a soft light." and E("pos")=="verb" and E("syn")=="glow, shine",st+str([E("def"),E("pos")]))
    pg.click("#save");pg.wait_for_timeout(100)
    # L: example without the word is dropped, dictionary does not supply one
    ev("(()=>{window.__aiImpl=async inp=>({pos:'noun',definition:'A sudden quiet or stillness.',synonyms:['silence'],antonyms:['noise'],example:'A completely unrelated sentence appears here.'});return 1})()")
    opn();gen("hush");chk("bad example dropped with a note",E("ex")=="" and "left blank" in pg.inner_text("#genst") and E("def").startswith("A sudden quiet"));pg.click("#save");pg.wait_for_timeout(100)
    # J/M: edit -> Regenerate; failed pronunciation keeps saved IPA
    ev("(()=>{window.__aiImpl=async inp=>({pos:'adjective',definition:'Peaceful and free from worry or noise.',synonyms:['calm'],antonyms:[],example:'She had a serene expression after the storm passed.'});return 1})()")
    pg.click('button[aria-label="Edit serene"]');chk("edit opens the review directly",pg.locator("#review").is_visible() and pg.locator("#genbtn").inner_text()=="Regenerate" and E("def").startswith("Calm"))
    DICT_FAIL[0]=True;pg.click("#genbtn");pg.wait_for_function("!document.getElementById('genbtn').disabled");pg.wait_for_timeout(80)
    chk("regenerate rewrites text, keeps saved IPA when lookup fails",E("def").startswith("Peaceful") and E("ipaUK")=="/sɪˈriːn/" and E("audioUS").endswith("serene-us.mp3") and "Pronunciation unavailable" in pg.inner_text("#genst"));DICT_FAIL[0]=False
    pg.click("#save");pg.wait_for_timeout(100);S2=W("serene");chk("edited entry persisted, same id, progress fields intact",S2["id"]==S["id"] and S2["def"].startswith("Peaceful") and S2["added"]==S["added"] and S2["box"]==0)
    # integration
    ev("location.hash='#garden'");pg.wait_for_timeout(150);chk("garden has a flower for every generated word",pg.locator("#beds .fl").count()==len(ls("ww.words.v1")))
    pg.reload();pg.wait_for_timeout(400);ev("location.hash='#library'");pg.wait_for_timeout(100);chk("generated entries persist after reload",W("serene")["ipaUK"]=="/sɪˈriːn/" and pg.locator("#cards .wcard").count()==len(ls("ww.words.v1")))
    ev("location.hash='#study'");pg.wait_for_timeout(100);pg.click('#stbody [data-act=start][data-n="5"]');chk("Memory Lane uses the generated words",ev("S.mode")=="run" and ev("words.some(w=>w.id===S.w.id)"))
    # mobile
    for wd in (390,320):
        pg.set_viewport_size({"width":wd,"height":800});ev("location.hash='#library'");pg.wait_for_timeout(100);opn();pg.fill("#f_term","serene") if False else None
        pg.click("#dlg [data-act=close]") if False else None
        pg.click("#dlg [data-act=close]");pg.click('button[aria-label="Edit serene"]');pg.click("#pdet summary") if not ev("document.getElementById('pdet').open") else None
        chk(f"form fits at {wd}",ev("document.getElementById('dlg').scrollWidth<=document.getElementById('dlg').clientWidth+1") and ev("document.documentElement.scrollWidth-innerWidth")<=1);pg.screenshot(path=f"s_gen{wd}.png");pg.click("#dlg [data-act=close]")
    pg.set_viewport_size({"width":1280,"height":900});ev("location.hash='#library'");pg.wait_for_timeout(100);opn();gen("serene") if False else None;pg.click("#dlg [data-act=close]");pg.click('button[aria-label="Edit serene"]');pg.wait_for_timeout(100);pg.screenshot(path="/tmp/s_gendesk.png")
    b.close()
print("\n%d checks, %d failed"%(len(R),R.count(False)));print("console/page errors:",ERR[:6])
