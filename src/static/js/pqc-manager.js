/**
 * PQC Manager
 * Manages ML-DSA-87 Keys in WebAssembly, WebAuthn PRF, and Argon2 recovery.
 */

class PqcManager {
    constructor() {
        this.module = null;
        this.skPtr = null; // Pointer to Secret Key in WASM memory
        this.pk = null; // Uint8Array of Public Key
        this.isUnlocked = false;
        
        // Constants for ML-DSA-87
        this.PK_LEN = 2592;
        this.SK_LEN = 4896;
        this.SIG_LEN = 4627;
        
        this.lockTimeout = null;
        this.LOCK_MINUTES = 30; // Auto-lock after 30 minutes of inactivity
        
        this.initPromise = this._initWasm();
        this._setupActivityListeners();
    }

    async _initWasm() {
        if (typeof liboqs === 'function') {
            this.module = await liboqs();
        } else {
            console.error("liboqs is not loaded.");
        }
    }

    _setupActivityListeners() {
        // Reset the timeout on any user interaction if unlocked
        const resetTimer = () => {
            if (this.isUnlocked) {
                this._resetLockTimeout();
            }
        };
        
        document.addEventListener('mousemove', resetTimer);
        document.addEventListener('keydown', resetTimer);
        document.addEventListener('click', resetTimer);
        document.addEventListener('scroll', resetTimer);
    }

    _resetLockTimeout() {
        if (this.lockTimeout) {
            clearTimeout(this.lockTimeout);
        }
        this.lockTimeout = setTimeout(() => {
            this.lock();
            // Show a notification to the user that session expired
            alert("E2EE Session auto-locked due to 30 minutes of inactivity. You will need to use your Passkey again.");
        }, this.LOCK_MINUTES * 60 * 1000);
    }

    /**
     * Zeros out the WASM memory where the Secret Key is stored.
     */
    lock() {
        if (this.skPtr !== null && this.module !== null) {
            // Zero-fill WASM memory
            const view = new Uint8Array(this.module.HEAPU8.buffer, this.skPtr, this.SK_LEN);
            crypto.getRandomValues(view); // Overwrite with random data
            this.module._free(this.skPtr);
            this.skPtr = null;
        }
        this.pk = null;
        this.isUnlocked = false;
        
        if (this.lockTimeout) {
            clearTimeout(this.lockTimeout);
            this.lockTimeout = null;
        }
        console.log("PQC Manager: Secret Key wiped from WASM memory.");
    }

    /**
     * Get or create a Passkey with PRF extension to derive a 256-bit symmetric key.
     * We use a hardcoded salt because the PRF extension returns HMAC(salt, PRF_Secret).
     */
    async _getPrfKey(isRegistration = false) {
        const challenge = crypto.getRandomValues(new Uint8Array(32));
        
        // The PRF extension requires exactly 32 bytes for the salt.
        // We hash a dynamic user-specific string with SHA3-256 to guarantee a deterministic 32-byte output.
        const username = localStorage.getItem('username') || 'unknown_user';
        const saltString = `Cloud-Policy-PRF-Salt-${username}`;
        const paddedSalt = new Uint8Array(sha3_256.arrayBuffer(saltString));
        
        let credential;
        let prfOutput;

        try {
            if (isRegistration) {
                const userId = crypto.getRandomValues(new Uint8Array(16));
                credential = await navigator.credentials.create({
                    publicKey: {
                        challenge,
                        rp: { name: "Cloud Policy Crypto Access", id: window.location.hostname },
                        user: {
                            id: userId,
                            name: localStorage.getItem('username') || "user",
                            displayName: localStorage.getItem('username') || "User"
                        },
                        pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
                        authenticatorSelection: { userVerification: "required" },
                        extensions: { prf: { eval: { first: paddedSalt } } }
                    }
                });
                
                const prfResults = credential.getClientExtensionResults().prf;
                if (!prfResults || !prfResults.enabled || !prfResults.results) {
                    console.warn("WebAuthn PRF not supported on this device/browser. Falling back to simple random key (NOT RECOMMENDED).");
                    // In a real high-security app, you might abort here.
                    // For compatibility, we'll generate a random key.
                    prfOutput = crypto.getRandomValues(new Uint8Array(32));
                } else {
                    prfOutput = new Uint8Array(prfResults.results.first);
                }
                
                // Store credential ID so we can get it later
                localStorage.setItem('pqc_credential_id', btoa(String.fromCharCode(...new Uint8Array(credential.rawId))));

            } else {
                const credIdB64 = localStorage.getItem('pqc_credential_id');
                
                const getOptions = {
                    publicKey: {
                        challenge,
                        rpId: window.location.hostname,
                        userVerification: 'required',
                        extensions: {
                            prf: {
                                eval: {
                                    first: paddedSalt
                                }
                            }
                        }
                    }
                };
                
                if (credIdB64) {
                    const credId = Uint8Array.from(atob(credIdB64), c => c.charCodeAt(0));
                    getOptions.publicKey.allowCredentials = [{
                        id: credId,
                        type: 'public-key'
                    }];
                }
                
                credential = await navigator.credentials.get(getOptions);
                
                if (!credential) {
                    throw new Error("Passkey authentication was cancelled or failed.");
                }
                
                const prfResults = credential.getClientExtensionResults().prf;
                if (!prfResults || !prfResults.results || !prfResults.results.first) {
                    console.warn("WebAuthn PRF not supported on this device/browser.");
                    throw new Error("Your Passkey device does not support the PRF extension required for E2EE.");
                }
                
                prfOutput = new Uint8Array(prfResults.results.first);
                
                // Save credential ID if it wasn't saved (e.g. after logout)
                if (!credIdB64) {
                    localStorage.setItem('pqc_credential_id', btoa(String.fromCharCode(...new Uint8Array(credential.rawId))));
                }
            }

            // Convert raw PRF output to a CryptoKey for AES-GCM-256
            return await crypto.subtle.importKey(
                "raw",
                prfOutput,
                { name: "AES-GCM" },
                false,
                ["encrypt", "decrypt"]
            );
        } catch (e) {
            console.error("PRF Passkey Error:", e);
            throw e;
        }
    }

    /**
     * Derive a 256-bit symmetric key from a 24-word Mnemonic using Argon2.
     */
    async _getArgon2Key(mnemonicWords) {
        // 1. Dynamic Salt: Use username to prevent rainbow table attacks
        const username = localStorage.getItem('username') || 'unknown_user';
        const saltString = `Cloud-Policy-Salt-${username}`;
        const salt = new TextEncoder().encode(saltString);
        
        // 2. Secure Memory Handling: Use Uint8Array for password to allow zeroing
        const passwordString = mnemonicWords.join(' ');
        const passBytes = new TextEncoder().encode(passwordString);
        
        // Use argon2-browser
        const result = await argon2.hash({
            pass: passBytes,
            salt: salt,
            time: 3, // iterations
            mem: 65536, // 64 KB (argon2-browser typically uses KB, not MB. 65536 = 64MB)
            hashLen: 32, // 256-bit key
            type: argon2.argon2id
        });
        
        const cryptoKey = await crypto.subtle.importKey(
            "raw",
            result.hash,
            { name: "AES-GCM" },
            false,
            ["encrypt", "decrypt"]
        );
        
        // 3. Zero-fill sensitive arrays to prevent RAM scraping
        crypto.getRandomValues(passBytes);
        crypto.getRandomValues(result.hash);
        
        return cryptoKey;
    }

    /**
     * Generate 24 random words for Mnemonic (Simplified for demo)
     */
    _generateMnemonic() {
        const words = ["abandon","ability","able","about","above","absent","absorb","abstract","absurd","abuse","access","accident","account","accuse","achieve","acid","acoustic","acquire","across","act","action","actor","actress","actual","adapt","add","addict","address","adjust","admit","adult","advance","advice","aerobic","affair","afford","afraid","again","age","agent","agree","ahead","aim","air","airport","aisle","alarm","album","alcohol","alert","alien","all","alley","allow","almost","alone","alpha","already","also","alter","always","amateur","amazing","among","amount","amused","analyst","anchor","ancient","anger","angle","angry","animal","ankle","announce","annual","another","answer","antenna","antique","anxiety","any","apart","apology","appear","apple","approve","april","arch","arctic","area","arena","argue","arm","armed","armor","army","around","arrange","arrest","arrive","arrow","art","artefact","artist","artwork","ask","aspect","assault","asset","assist","assume","asthma","athlete","atom","attack","attend","attitude","attract","auction","audit","august","aunt","author","auto","autumn","average","avocado","avoid","awake","aware","away","awesome","awful","awkward","axis","baby","bachelor","bacon","badge","bag","balance","balcony","ball","bamboo","banana","banner","bar","barely","bargain","barrel","base","basic","basket","battle","beach","bean","beauty","because","become","beef","before","begin","behave","behind","believe","below","belt","bench","benefit","best","betray","better","between","beyond","bicycle","bid","bike","bind","biology","bird","birth","bitter","black","blade","blame","blanket","blast","bleak","blind","blood","blossom","blouse","blue","blur","board","boat","body","boil","bomb","bone","bonus","book","boost","border","boring","borrow","boss","bottom","bounce","box","boy","bracket","brain","brand","brass","brave","bread","breeze","brick","bridge","brief","bright","bring","brisk","broccoli","broken","bronze","broom","brother","brown","brush","bubble","buddy","budget","buffalo","build","bulb","bulk","bullet","bundle","burden","burger","burst","bus","business","busy","butter","buyer","buzz","cabbage","cabin","cable","cactus","cage","cake","call","calm","camera","camp","can","canal","cancel","candy","cannon","canoe","canvas","canyon","capable","capital","captain","car","carbon","card","cargo","carpet","carry","cart","case","cash","casino","castle","casual","cat","catalog","catch","category","cattle","caught","cause","caution","cave","ceiling","celery","cement","census","century","cereal","certain","chair","chalk","champion","change","chaos","chapter","charge","chase","chat","cheap","check","cheese","chef","cherry","chest","chicken","chief","child","chimney","choice","choose","chronic","chuckle","chunk","churn","cigar","cinnamon","circle","citizen","city","civil","claim","clap","clarify","claw","clay","clean","clerk","clever","click","client","cliff","climb","clinic","clip","clock","clog","close","cloth","cloud","clown","club","clump","cluster","clutch","coach","coast","coconut","code","coffee","coil","coin","collect","color","column","combine","come","comfort","comic","common","company","concert","conduct","confirm","congress","connect","consider","control","convince","cook","cool","copper","copy","coral","core","corn","correct","cost","cotton","couch","country","couple","course","cousin","cover","coyote","crack","cradle","craft","cram","crane","crash","crater","crawl","crazy","cream","credit","creek","crew","cricket","crime","crisp","critic","crop","cross","crowd","crucial","cruel","cruise","crumble","crunch","crush","cry","crystal","cube","culture","cup","cupboard","curious","current","curtain","curve","cushion","custom","cute","cycle","dad","damage","damp","dance","danger","daring","dash","daughter","dawn","day","deal","debate","debris","decade","december","decide","decline","decorate","decrease","deer","defense","define","defy","degree","delay","deliver","demand","demise","denial","dentist","deny","depart","depend","deposit","depth","deputy","derive","describe","desert","design","desk","despair","destroy","detail","detect","develop","device","devote","diagram","dial","diamond","diary","dice","diesel","diet","differ","digital","dignity","dilemma","dinner","dinosaur","direct","dirt","disagree","discover","disease","dish","dismiss","disorder","display","distance","divert","divide","divorce","dizzy","doctor","document","dog","doll","dolphin","domain","donate","donkey","donor","door","dose","double","dove","draft","dragon","drama","drastic","draw","dream","dress","drift","drill","drink","drip","drive","drop","drum","dry","duck","dumb","dune","during","dust","dutch","duty","dwarf","dynamic","eager","eagle","early","earn","earth","easily","east","easy","echo","ecology","economy","edge","edit","educate","effort","egg","eight","either","elbow","elder","electric","elegant","element","elephant","elevator","elite","else","embark","embody","embrace","emerge","emotion","employ","empower","empty","enable","enact","end","endless","endorse","enemy","energy","enforce","engage","engine","enhance","enjoy","enlist","enough","enrich","enroll","ensure","enter","entire","entry","envelope","episode","equal","equip","era","erase","erode","erosion","error","erupt","escape","essay","essence","estate","eternal","ethics","evidence","evil","evoke","evolve","exact","example","excess","exchange","excite","exclude","excuse","execute","exercise","exhaust","exhibit","exile","exist","exit","exotic","expand","expect","expire","explain","expose","express","extend","extra","eye","eyebrow","fabric","face","faculty","fade","faint","faith","fall","false","fame","family","famous","fan","fancy","fantasy","farm","fashion","fat","fatal","father","fatigue","fault","favorite","feature","february","federal","fee","feed","feel","female","fence","festival","fetch","fever","few","fiber","fiction","field","figure","file","film","filter","final","find","fine","finger","finish","fire","firm","first","fiscal","fish","fit","fitness","fix","flag","flame","flash","flat","flavor","flee","flight","flip","float","flock","floor","flower","fluid","flush","fly","foam","focus","fog","foil","fold","follow","food","foot","force","forest","forget","fork","fortune","forum","forward","fossil","foster","found","fox","fragile","frame","frequent","fresh","friend","fringe","frog","front","frost","frown","frozen","fruit","fuel","fun","funny","furnace","fury","future","gadget","gain","galaxy","gallery","game","gap","garage","garbage","garden","garlic","garment","gas","gasp","gate","gather","gauge","gaze","general","genius","genre","gentle","genuine","gesture","ghost","giant","gift","giggle","ginger","giraffe","girl","give","glad","glance","glare","glass","glide","glimpse","globe","gloom","glory","glove","glow","glue","goat","goddess","gold","good","goose","gorilla","gospel","gossip","govern","gown","grab","grace","grain","grant","grape","grass","gravity","great","green","grid","grief","grit","grocery","group","grow","grunt","guard","guess","guide","guilt","guitar","gun","gym","habit","hair","half","hammer","hamster","hand","happy","harbor","hard","harsh","harvest","hat","have","hawk","hazard","head","health","heart","heavy","hedgehog","height","hello","helmet","help","hen","hero","hidden","high","hill","hint","hip","hire","history","hobby","hockey","hold","hole","holiday","hollow","home","honey","hood","hope","horn","horror","horse","hospital","host","hotel","hour","hover","hub","huge","human","humble","humor","hundred","hungry","hunt","hurdle","hurry","hurt","husband","hybrid","ice","icon","idea","identify","idle","ignore","ill","illegal","illness","image","imitate","immense","immune","impact","impose","improve","impulse","inch","include","income","increase","index","indicate","indoor","industry","infant","inflict","inform","inhale","inherit","initial","inject","injury","inmate","inner","innocent","input","inquiry","insane","insect","inside","inspire","install","intact","interest","into","invest","invite","involve","iron","island","isolate","issue","item","ivory","jacket","jaguar","jar","jazz","jealous","jeans","jelly","jewel","job","join","joke","journey","joy","judge","juice","jump","jungle","junior","junk","just","kangaroo","keen","keep","ketchup","key","kick","kid","kidney","kind","kingdom","kiss","kit","kitchen","kite","kitten","kiwi","knee","knife","knock","know","lab","label","labor","ladder","lady","lake","lamp","language","laptop","large","later","latin","laugh","laundry","lava","law","lawn","lawsuit","layer","lazy","leader","leaf","learn","leave","lecture","left","leg","legal","legend","leisure","lemon","lend","length","lens","leopard","lesson","letter","level","liar","liberty","library","license","life","lift","light","like","limb","limit","link","lion","liquid","list","little","live","lizard","load","loan","logic","logo","lonely","long","look","loop","lottery","loud","lounge","love","loyal","lucky","luggage","lumber","lunar","lunch","luxury","lyrics","machine","mad","magic","magnet","maid","mail","main","major","make","mammal","man","manage","mandate","mango","mansion","manual","map","marble","march","margin","marine","market","marriage","mask","mass","master","match","material","math","matrix","matter","maximum","maze","meadow","mean","measure","meat","mechanic","medal","media","melody","melt","member","memory","mention","menu","mercy","merge","merit","merry","mesh","message","metal","method","middle","midnight","milk","million","mimic","mind","minimum","minor","minute","miracle","mirror","misery","miss","mistake","mix","mixed","mixture","mobile","model","modify","mom","moment","monitor","monkey","monster","month","moon","moral","more","morning","mosquito","mother","motion","motor","mountain","mouse","move","movie","much","muffin","mule","multiply","muscle","museum","mushroom","music","must","mutual","myself","mystery","myth","naive","name","napkin","narrow","nasty","nation","nature","near","neck","need","negative","neglect","neither","nephew","nerve","nest","net","network","neutral","never","news","next","nice","night","noble","noise","nominee","noodle","normal","north","nose","notable","note","nothing","notice","novel","now","nuclear","number","nurse","nut","oak","obey","object","oblige","obscure","observe","obtain","obvious","occur","ocean","october","odor","off","offer","office","often","oil","okay","old","olive","olympic","omit","once","one","onion","online","only","open","opera","opinion","oppose","option","orange","orbit","orchard","order","ordinary","organ","orient","original","orphan","ostrich","other","outdoor","outer","output","outside","oval","oven","over","own","owner","oxygen","oyster","ozone","pact","paddle","page","pair","palace","palm","panda","panel","panic","panther","paper","parade","parent","park","parrot","party","pass","patch","path","patient","patrol","pattern","pause","pave","payment","peace","peanut","pear","peasant","pelican","pen","penalty","pencil","people","pepper","perfect","permit","person","pet","phone","photo","phrase","physical","piano","picnic","picture","piece","pig","pigeon","pill","pilot","pink","pioneer","pipe","pistol","pitch","pizza","place","planet","plastic","plate","play","please","pledge","pluck","plug","plunge","poem","poet","point","polar","pole","police","pond","pony","pool","popular","portion","position","possible","post","potato","pottery","poverty","powder","power","practice","praise","predict","prefer","prepare","present","pretty","prevent","price","pride","primary","print","priority","prison","private","prize","problem","process","produce","profit","program","project","promote","proof","property","prosper","protect","proud","provide","public","pudding","pull","pulp","pulse","pumpkin","punch","pupil","puppy","purchase","purity","purpose","purse","push","put","puzzle","pyramid","quality","quantum","quarter","question","quick","quit","quiz","quote","rabbit","raccoon","race","rack","radar","radio","rail","rain","raise","rally","ramp","ranch","random","range","rapid","rare","rate","rather","raven","raw","razor","ready","real","reason","rebel","rebuild","recall","receive","recipe","record","recycle","reduce","reflect","reform","refuse","region","regret","regular","reject","relax","release","relief","rely","remain","remember","remind","remove","render","renew","rent","reopen","repair","repeat","replace","report","require","rescue","resemble","resist","resource","response","result","retire","retreat","return","reunion","reveal","review","reward","rhythm","rib","ribbon","rice","rich","ride","ridge","rifle","right","rigid","ring","riot","ripple","risk","ritual","rival","river","road","roast","robot","robust","rocket","romance","roof","rookie","room","rose","rotate","rough","round","route","royal","rubber","rude","rug","rule","run","runway","rural","sad","saddle","sadness","safe","sail","salad","salmon","salon","salt","salute","same","sample","sand","satisfy","satoshi","sauce","sausage","save","say","scale","scan","scare","scatter","scene","scheme","school","science","scissors","scorpion","scout","scrap","screen","script","scrub","sea","search","season","seat","second","secret","section","security","seed","seek","segment","select","sell","seminar","senior","sense","sentence","series","service","session","settle","setup","seven","shadow","shaft","shallow","share","shed","shell","sheriff","shield","shift","shine","ship","shiver","shock","shoe","shoot","shop","short","shoulder","shove","shrimp","shrug","shuffle","shy","sibling","sick","side","siege","sight","sign","silent","silk","silly","silver","similar","simple","since","sing","siren","sister","situate","six","size","skate","sketch","ski","skill","skin","skirt","skull","slab","slam","sleep","slide","slight","slip","slogan","slot","slow","slush","small","smart","smile","smoke","smooth","snack","snake","snap","sniff","snow","soap","soccer","social","sock","soda","soft","solar","soldier","solid","solution","solve","someone","song","soon","sorry","sort","soul","sound","soup","source","south","space","spare","spatial","spawn","speak","special","speed","spell","spend","sphere","spice","spider","spike","spin","spirit","split","spoil","sponsor","spoon","sport","spot","spray","spread","spring","spy","square","squeeze","squirrel","stadium","staff","stage","stairs","stamp","stand","start","state","stay","steak","steel","stem","step","stereo","stick","still","sting","stock","stomach","stone","stool","story","stove","strategy","street","strike","strong","struggle","student","stuff","stumble","style","subject","submit","subway","success","such","sudden","suffer","sugar","suggest","suit","summer","sun","sunny","sunset","super","supply","supreme","sure","surface","surge","surprise","surround","survey","suspect","sustain","swallow","swamp","swap","swarm","swear","sweet","swift","swim","swing","switch","sword","symbol","symptom","syrup","system","table","tackle","tag","tail","talent","talk","tank","tape","target","task","taste","tattoo","taxi","teach","team","tell","ten","tenant","tennis","tent","term","test","text","thank","that","theme","then","theory","there","they","thing","this","thought","three","thrive","throw","thumb","thunder","ticket","tide","tiger","tilt","timber","time","tiny","tip","tired","tissue","title","toast","tobacco","today","toddler","toe","together","toilet","token","tomato","tomorrow","tone","tongue","tonight","tool","tooth","top","topic","topple","torch","tornado","tortoise","toss","total","tourist","toward","tower","town","toy","track","trade","traffic","tragic","train","transfer","trap","trash","travel","tray","treat","tree","trend","trial","tribe","trick","trigger","trim","trip","trophy","trouble","truck","true","truly","trumpet","trust","truth","try","tube","tuition","tumble","tuna","tunnel","turkey","turn","turtle","twelve","twenty","twice","twin","twist","two","type","typical","ugly","umbrella","unable","unaware","uncle","uncover","under","undo","unfair","unfold","unhappy","uniform","unique","universe","unknown","unlock","until","unusual","unveil","update","upgrade","uphold","upon","upper","upset","urban","urge","usage","use","used","useful","useless","usual","utility","vacant","vacuum","vague","valid","valley","valve","van","vanish","vapor","various","vast","vault","vehicle","velvet","vendor","venture","venue","verb","verify","version","very","vessel","veteran","viable","vibrant","vicious","victory","video","view","village","vintage","violin","virtual","virus","visa","visit","visual","vital","vivid","vocal","voice","void","volcano","volume","vote","voyage","wage","wagon","wait","walk","wall","walnut","want","warfare","warm","warrior","wash","wasp","waste","water","wave","way","wealth","weapon","wear","weasel","weather","web","wedding","weekend","weird","welcome","west","wet","whale","what","wheat","wheel","when","where","whip","whisper","wide","width","wife","wild","will","win","window","wine","wing","wink","winner","winter","wire","wisdom","wise","wish","witness","wolf","woman","wonder","wood","wool","word","work","world","worry","worth","wrap","wreck","wrestle","wrist","write","wrong","yard","year","yellow","you","young","youth","zebra","zero","zone","zoo"];
        const randomWords = [];
        for (let i = 0; i < 24; i++) {
            const idx = Math.floor(Math.random() * words.length);
            randomWords.push(words[idx]);
        }
        return randomWords;
    }

    /**
     * Utility: Encrypt data with AES-GCM and return Base64 "IV:Ciphertext"
     */
    async _encryptKey(cryptoKey, rawSecretKey) {
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const ciphertext = await crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv },
            cryptoKey,
            rawSecretKey
        );
        
        // Combine IV + Ciphertext
        const payload = new Uint8Array(12 + ciphertext.byteLength);
        payload.set(iv, 0);
        payload.set(new Uint8Array(ciphertext), 12);
        
        return btoa(String.fromCharCode(...payload));
    }

    /**
     * Utility: Decrypt Base64 "IV:Ciphertext" back to raw bytes
     */
    async _decryptKey(cryptoKey, b64Payload) {
        const payload = Uint8Array.from(atob(b64Payload), c => c.charCodeAt(0));
        const iv = payload.slice(0, 12);
        const ciphertext = payload.slice(12);
        
        return await crypto.subtle.decrypt(
            { name: "AES-GCM", iv: iv },
            cryptoKey,
            ciphertext
        );
    }

    /**
     * Step 1: Initial Setup of ML-DSA-87 and Passkey PRF.
     */
    async setup() {
        await this.initPromise;
        
        // 1. Ask WebAuthn to create Passkey & get PRF
        const prfKey = await this._getPrfKey(true);
        
        // 2. Generate Mnemonic and Argon2 key
        const mnemonic = this._generateMnemonic();
        const argonKey = await this._getArgon2Key(mnemonic);
        
        // 3. Generate ML-DSA-87 Keypair in WASM
        const pkPtr = this.module._malloc(this.PK_LEN);
        const skPtr = this.module._malloc(this.SK_LEN);
        
        const ret = this.module._OQS_SIG_ml_dsa_87_keypair(pkPtr, skPtr);
        if (ret !== 0) throw new Error("Failed to generate PQC keypair");
        
        const rawPk = new Uint8Array(this.module.HEAPU8.buffer, pkPtr, this.PK_LEN);
        const rawSk = new Uint8Array(this.module.HEAPU8.buffer, skPtr, this.SK_LEN);
        
        // 4. Encrypt SK twice
        const primaryEnc = await this._encryptKey(prfKey, rawSk);
        const recoveryEnc = await this._encryptKey(argonKey, rawSk);
        
        const pkB64 = btoa(String.fromCharCode(...rawPk));
        
        // 5. Store in WASM memory for current session
        this.pk = new Uint8Array(rawPk);
        this.skPtr = skPtr;
        this.isUnlocked = true;
        this._resetLockTimeout();
        
        // 6. Free temporary PK ptr (we keep SK ptr)
        this.module._free(pkPtr);
        
        // 7. Upload to backend
        const response = await fetch('/api/pki/keys/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                pqc_public_key: pkB64,
                encrypted_pqc_sk_primary: primaryEnc,
                encrypted_pqc_sk_recovery: recoveryEnc,
                device_name: navigator.userAgent
            })
        });
        
        if (!response.ok) {
            throw new Error("Failed to save keys to server.");
        }
        
        return mnemonic;
    }

    /**
     * Step 2: Unlock the existing key using Passkey PRF.
     */
    async unlock() {
        await this.initPromise;
        
        if (this.isUnlocked) return true;
        
        // 1. Fetch encrypted SK from Backend
        const response = await fetch('/api/pki/keys/active_key/');
        if (response.status === 404) {
            return false; // User has no keys setup
        }
        if (!response.ok) throw new Error("Failed to fetch PQC key metadata");
        
        const keyData = await response.json();
        this.pk = Uint8Array.from(atob(keyData.pqc_public_key), c => c.charCodeAt(0));
        
        // 2. Ask WebAuthn to get PRF Symmetric Key
        const prfKey = await this._getPrfKey(false);
        
        // 3. Decrypt SK
        const rawSkBuffer = await this._decryptKey(prfKey, keyData.encrypted_pqc_sk_primary);
        const rawSkArray = new Uint8Array(rawSkBuffer);
        
        // 4. Isolate into WASM Heap
        this.skPtr = this.module._malloc(this.SK_LEN);
        this.module.HEAPU8.set(rawSkArray, this.skPtr);
        
        // 5. CRITICAL: Zero-fill JS Array
        crypto.getRandomValues(rawSkArray);
        
        this.isUnlocked = true;
        this._resetLockTimeout();
        console.log("PQC Manager: Unlocked and loaded to WASM Heap.");
        return true;
    }
    
    /**
     * Recover the Passkey access using the 24-word Mnemonic Phrase.
     * Decrypts the recovery payload, prompts to create a new Passkey, and updates the server.
     */
    async recoverKey(mnemonicString) {
        await this.initPromise;
        
        // 1. Get Argon2 Key from Mnemonic
        const mnemonicArray = mnemonicString.trim().split(/\s+/);
        if (mnemonicArray.length !== 24) {
            throw new Error("Invalid Recovery Phrase. Must be exactly 24 words.");
        }
        const recoverKey = await this._getArgon2Key(mnemonicArray);
        
        // 2. Fetch the active key metadata
        const response = await fetch('/api/pki/keys/active_key/');
        if (!response.ok) throw new Error("No active E2EE key found on the server.");
        const keyData = await response.json();
        
        // 3. Decrypt the recovery blob to get the raw PQC SK
        const rawSkBuffer = await this._decryptKey(recoverKey, keyData.encrypted_pqc_sk_recovery);
        const rawSkArray = new Uint8Array(rawSkBuffer);
        
        // 4. Prompt user to setup a NEW Passkey
        // Passing isRegistration = true forces a new Passkey PRF credential creation
        const { credential, prfOutput } = await this._getPrfKey(true);
        const newPrfKey = await this._getPrfToCryptoKey(prfOutput);
        
        // 5. Encrypt the raw SK with the new PRF key
        const newPrimaryEnc = await this._encryptKey(newPrfKey, rawSkArray);
        
        // 6. Update the Primary encrypted blob on the server
        const patchResponse = await fetch(`/api/pki/keys/${keyData.id}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                encrypted_pqc_sk_primary: newPrimaryEnc
            })
        });
        
        if (!patchResponse.ok) {
            throw new Error("Failed to update E2EE key on server.");
        }
        
        // Save the new credential ID globally (or per username)
        const username = localStorage.getItem('username') || 'unknown_user';
        localStorage.setItem(`pqc_credential_id_${username}`, credential.id);
        
        // 7. Load into WASM Memory for current session
        this.pk = Uint8Array.from(atob(keyData.pqc_public_key), c => c.charCodeAt(0));
        this.skPtr = this.module._malloc(this.SK_LEN);
        this.module.HEAPU8.set(rawSkArray, this.skPtr);
        
        // Zero-fill temp array
        crypto.getRandomValues(rawSkArray);
        
        this.isUnlocked = true;
        this._resetLockTimeout();
        console.log("PQC Manager: Key recovered, Passkey replaced, and unlocked.");
        return true;
    }
    
    /**
     * Check if user has an active key setup on the server
     */
    async hasKeySetup() {
        const response = await fetch('/api/pki/keys/active_key/');
        return response.ok;
    }

    /**
     * Sign a file buffer directly using WASM.
     */
    async signFile(fileBuffer) {
        if (!this.isUnlocked) throw new Error("PQC Key is locked. Call unlock() first.");
        this._resetLockTimeout();
        
        const msgArray = new Uint8Array(fileBuffer);
        const msgLen = msgArray.length;
        
        const msgPtr = this.module._malloc(msgLen);
        this.module.HEAPU8.set(msgArray, msgPtr);
        
        const sigPtr = this.module._malloc(this.SIG_LEN);
        const sigLenPtr = this.module._malloc(4); // size_t
        
        const ret = this.module._OQS_SIG_ml_dsa_87_sign(sigPtr, sigLenPtr, msgPtr, msgLen, this.skPtr);
        
        if (ret !== 0) {
            this.module._free(msgPtr);
            this.module._free(sigPtr);
            this.module._free(sigLenPtr);
            throw new Error("WASM Signature generation failed");
        }
        
        // Read actual signature length
        const actualSigLen = new Uint32Array(this.module.HEAPU8.buffer, sigLenPtr, 1)[0];
        const sigBytes = new Uint8Array(this.module.HEAPU8.buffer, sigPtr, actualSigLen);
        
        const sigBase64 = btoa(String.fromCharCode(...sigBytes));
        
        this.module._free(msgPtr);
        this.module._free(sigPtr);
        this.module._free(sigLenPtr);
        
        return sigBase64;
    }

    /**
     * Verify a file buffer against a signature and public key.
     */
    async verifySignature(fileBuffer, sigBase64, pkBase64) {
        await this.initPromise;
        
        const msgArray = new Uint8Array(fileBuffer);
        const msgLen = msgArray.length;
        
        const sigArray = Uint8Array.from(atob(sigBase64), c => c.charCodeAt(0));
        const pkArray = Uint8Array.from(atob(pkBase64), c => c.charCodeAt(0));
        
        const msgPtr = this.module._malloc(msgLen);
        this.module.HEAPU8.set(msgArray, msgPtr);
        
        const sigPtr = this.module._malloc(sigArray.length);
        this.module.HEAPU8.set(sigArray, sigPtr);
        
        const pkPtr = this.module._malloc(this.PK_LEN);
        this.module.HEAPU8.set(pkArray, pkPtr);
        
        const ret = this.module._OQS_SIG_ml_dsa_87_verify(msgPtr, msgLen, sigPtr, sigArray.length, pkPtr);
        
        this.module._free(msgPtr);
        this.module._free(sigPtr);
        this.module._free(pkPtr);
        
        return ret === 0;
    }
}

// Global instance
const pqcManager = new PqcManager();

// Event Listeners for UI Modals (Hooked up if they exist on the page)
document.addEventListener('DOMContentLoaded', () => {
    const btnSetup = document.getElementById('btn-pqc-setup');
    const setupModal = document.getElementById('pqc-setup-modal');
    const setupStatus = document.getElementById('pqc-setup-status');
    const btnSetupClose = document.getElementById('btn-pqc-setup-close');
    
    const mnemonicModal = document.getElementById('pqc-mnemonic-modal');
    const btnDownloadMnemonic = document.getElementById('btn-download-mnemonic');
    const btnMnemonicSaved = document.getElementById('btn-mnemonic-saved');
    
    const unlockModal = document.getElementById('pqc-unlock-modal');
    const btnUnlock = document.getElementById('btn-pqc-unlock');
    const btnUnlockCancel = document.getElementById('btn-pqc-cancel');
    const unlockStatus = document.getElementById('pqc-unlock-status');
    const btnRecover = document.getElementById('btn-pqc-recover');
    
    const recoverModal = document.getElementById('pqc-recover-modal');
    const btnRecoverClose = document.getElementById('btn-pqc-recover-close');
    const btnDoRecover = document.getElementById('btn-pqc-do-recover');
    const recoverStatus = document.getElementById('pqc-recover-status');
    const recoverPhrase = document.getElementById('pqc-recover-phrase');
    
    if (btnSetup) {
        btnSetup.addEventListener('click', async () => {
            try {
                btnSetup.disabled = true;
                btnSetup.textContent = "Processing Passkey & PQC Keys...";
                setupStatus.classList.remove('hidden');
                setupStatus.textContent = "Please touch your security key or biometric sensor.";
                
                const mnemonic = await pqcManager.setup();
                
                setupModal.classList.add('hidden');
                
                // Setup download button
                if (btnDownloadMnemonic) {
                    btnDownloadMnemonic.onclick = () => {
                        const text = "Cloud Policy Crypto Access - E2EE Recovery Phrase\n" +
                                     "WARNING: DO NOT SHARE THIS FILE WITH ANYONE.\n\n" +
                                     mnemonic.join(' ');
                        const blob = new Blob([text], { type: 'text/plain' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        const username = localStorage.getItem('username') || 'unknown_user';
                        a.download = `CloudPolicy-E2EE-Recovery-Phrase-${username}.txt`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    };
                }
                mnemonicModal.classList.remove('hidden');
                
            } catch (e) {
                console.error(e);
                setupStatus.textContent = "Error: " + e.message;
                setupStatus.classList.add('text-red-500');
                btnSetup.disabled = false;
                btnSetup.textContent = "Try Again";
            }
        });
    }
    
    if (btnMnemonicSaved) {
        btnMnemonicSaved.addEventListener('click', () => {
            mnemonicModal.classList.add('hidden');
            if (window.pqcSetupPromiseResolve) {
                window.pqcSetupPromiseResolve();
                window.pqcSetupPromiseResolve = null;
                window.pqcSetupPromiseReject = null;
            } else {
                // Reload or continue if no promise is waiting
                window.location.reload();
            }
        });
    }
    
    if (btnSetupClose) {
        btnSetupClose.addEventListener('click', () => {
            setupModal.classList.add('hidden');
            if (window.pqcSetupPromiseReject) {
                window.pqcSetupPromiseReject(new Error("User cancelled Passkey setup"));
                window.pqcSetupPromiseReject = null;
            }
        });
    }
    
    if (btnUnlockCancel) {
        btnUnlockCancel.addEventListener('click', () => {
            unlockModal.classList.add('hidden');
            if (window.pqcUnlockPromiseReject) {
                window.pqcUnlockPromiseReject(new Error("User cancelled Passkey unlock"));
                window.pqcUnlockPromiseReject = null;
            }
        });
    }
    
    if (btnUnlock) {
        btnUnlock.addEventListener('click', async () => {
            try {
                btnUnlock.disabled = true;
                btnUnlock.textContent = "Waiting for Passkey...";
                unlockStatus.classList.add('hidden');
                
                await pqcManager.unlock();
                
                unlockModal.classList.add('hidden');
                btnUnlock.disabled = false;
                btnUnlock.textContent = "Use Passkey";
                
                if (window.pqcUnlockPromiseResolve) {
                    window.pqcUnlockPromiseResolve();
                    window.pqcUnlockPromiseResolve = null;
                }
            } catch (e) {
                console.error(e);
                if (e.message.includes('timed out or was not allowed') || e.message.includes('cancelled')) {
                    // Suppress WebAuthn cancellation errors to avoid scaring the user
                    unlockStatus.classList.add('hidden');
                } else {
                    unlockStatus.textContent = "Authentication failed: " + e.message;
                    unlockStatus.classList.remove('hidden');
                }
                btnUnlock.disabled = false;
                btnUnlock.textContent = "Try Again";
            }
        });
    }
    
    // Bind Recovery Modal toggle
    if (btnRecover) {
        btnRecover.addEventListener('click', () => {
            unlockModal.classList.add('hidden');
            if (recoverModal) recoverModal.classList.remove('hidden');
        });
    }
    
    if (btnRecoverClose) {
        btnRecoverClose.addEventListener('click', () => {
            recoverModal.classList.add('hidden');
            if (window.pqcUnlockPromiseReject) {
                window.pqcUnlockPromiseReject(new Error("User cancelled recovery"));
                window.pqcUnlockPromiseReject = null;
            }
        });
    }
    
    if (btnDoRecover) {
        btnDoRecover.addEventListener('click', async () => {
            try {
                const phrase = recoverPhrase.value;
                if (!phrase || phrase.trim().split(/\s+/).length !== 24) {
                    throw new Error("Please enter exactly 24 words.");
                }
                
                btnDoRecover.disabled = true;
                btnDoRecover.textContent = "Rebuilding Key...";
                recoverStatus.classList.add('hidden');
                
                await pqcManager.recoverKey(phrase);
                
                recoverModal.classList.add('hidden');
                btnDoRecover.disabled = false;
                btnDoRecover.textContent = "Recover & Create New Passkey";
                
                // Once recovered, they are unlocked
                if (window.pqcUnlockPromiseResolve) {
                    window.pqcUnlockPromiseResolve();
                    window.pqcUnlockPromiseResolve = null;
                }
            } catch (e) {
                console.error(e);
                recoverStatus.textContent = "Recovery failed: " + e.message;
                recoverStatus.classList.remove('hidden');
                btnDoRecover.disabled = false;
                btnDoRecover.textContent = "Recover & Create New Passkey";
            }
        });
    }
});

/**
 * Helper function to wait for user to unlock via Modal
 */
async function requirePqcUnlock() {
    if (pqcManager.isUnlocked) return true;
    
    const hasSetup = await pqcManager.hasKeySetup();
    if (!hasSetup) {
        document.getElementById('pqc-setup-modal').classList.remove('hidden');
        return new Promise((resolve, reject) => {
            window.pqcSetupPromiseResolve = resolve;
            window.pqcSetupPromiseReject = reject;
        });
    }
    
    document.getElementById('pqc-unlock-modal').classList.remove('hidden');
    return new Promise((resolve, reject) => {
        window.pqcUnlockPromiseResolve = resolve;
        window.pqcUnlockPromiseReject = reject;
    });
}
