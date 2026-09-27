"""Multilingual message catalogue — English, Shona, Ndebele."""

SUPPORTED_LANGUAGES = ("en", "sn", "nd")

LANGUAGE_NAMES = {
    "en": "English",
    "sn": "ChiShona",
    "nd": "isiNdebele",
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    lang = lang if lang in SUPPORTED_LANGUAGES else "en"
    catalogue = _MESSAGES.get(key, {})
    text = catalogue.get(lang) or catalogue.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


_USSD_MENU = {
    "en": "CON SafePass\n1. Register pregnancy\n2. Check-in visit\n3. Report danger sign\n4. My pregnancies\n5. Language",
    "sn": "CON SafePass\n1. Nyoresa pamuviri\n2. Pinda visit\n3. Rapota chiratidzo\n4. Pamuviri dzangu\n5. Mutauro",
    "nd": "CON SafePass\n1. Bhalisa ukukhulelwa\n2. Ukungena visit\n3. Bika uphawu\n4. Ukukhulelwa kwami\n5. Ulwimi",
}

_LANGUAGE_MENU = {
    "en": "CON Select language:\n1. English\n2. ChiShona\n3. isiNdebele",
    "sn": "CON Sarudza mutauro:\n1. English\n2. ChiShona\n3. isiNdebele",
    "nd": "CON Khetha ulwimi:\n1. English\n2. ChiShona\n3. isiNdebele",
}

_MESSAGES = {
    "ussd.menu": _USSD_MENU,
    "ussd.language_menu": _LANGUAGE_MENU,
    "ussd.language_set": {
        "en": "END Language set to English.",
        "sn": "END Mutauro waiswa kuChiShona.",
        "nd": "END Ulwimi usethelwe isiNdebele.",
    },
    "registered": {
        "en": "SafePass: Registered at clinic. Ref {ref}.",
        "sn": "SafePass: Wanyoreswa kuchipatara. Ref {ref}.",
        "nd": "SafePass: Ubhalisiwe esibhedlela. Ref {ref}.",
    },
    "danger_sign_patient": {
        "en": "SafePass: Danger sign recorded. Go to clinic if symptoms worsen. Ref {ref}.",
        "sn": "SafePass: Chiratidzo chakanongwa. Enda kuchipatara kana zvikaoma. Ref {ref}.",
        "nd": "SafePass: Upuhawu lubikiwe. Iya esibhedlela uma kube kubi. Ref {ref}.",
    },
    "referral_patient": {
        "en": "SAFEPASS: Go to {hospital}. Show ref {ref}. Reason: {reason}",
        "sn": "SAFEPASS: Enda ku{hospital}. Ratidza ref {ref}. Chikonzero: {reason}",
        "nd": "SAFEPASS: Iya ku{hospital}. Khombisa ref {ref}. Isizathu: {reason}",
    },
    "edd_7": {
        "en": "SafePass EDD: 7 days until due date. Confirm birth plan & transport. Ref {ref}.",
        "sn": "SafePass EDD: Mazuva 7 kusvika zuva rekuzvara. Sungirira hurongwa hwekuzvara. Ref {ref}.",
        "nd": "SafePass EDD: Izinsuku ezi-7 kuze kube usuku lokuzala. Lungiselela uhlelo lokuzala. Ref {ref}.",
    },
    "edd_1": {
        "en": "SafePass EDD: Due tomorrow. Go to facility if labour starts. Ref {ref}.",
        "sn": "SafePass EDD: Zvino mangwana. Enda kuchipatara kana kurwadziwa kwatanga. Ref {ref}.",
        "nd": "SafePass EDD: Kusasa. Iya esibhedlela uma ukuqala ukuhlaza. Ref {ref}.",
    },
    "edd_0": {
        "en": "SafePass EDD: Today is your due date. Contact clinic if you need help. Ref {ref}.",
        "sn": "SafePass EDD: Nhasi zuva rekuzvara. Batana nekuchipatara kana uchida rubatsiro. Ref {ref}.",
        "nd": "SafePass EDD: Namuhla usuku lokuzala. Xhumana nesibhedlela uma udinga usizo. Ref {ref}.",
    },
    "followup_adolescent_anc": {
        "en": "SafePass: Your ANC follow-up is due. Please visit the clinic this week. Ref {ref}.",
        "sn": "SafePass: Kufamba kwako kweANC kwakakodzera. Ndapota enda kuchipatara svondo rino. Ref {ref}.",
        "nd": "SafePass: Ukulandelelwa kwakho kwe-ANC kufanele. Sicela uvakashe esibhedlela kuleli viki. Ref {ref}.",
    },
    "followup_post_term": {
        "en": "SafePass: You are past your due date. Contact the clinic today for assessment. Ref {ref}.",
        "sn": "SafePass: Wapfuura zuva rekuzvara. Batana nekuchipatara nhasi kuti uongororwe. Ref {ref}.",
        "nd": "SafePass: Usudlule usuku lokuzala. Xhumana nesibhedlela namuhla ukuze uhlolwe. Ref {ref}.",
    },
    "followup_twins": {
        "en": "SafePass: Twin pregnancy — attend all ANC visits and follow your birth plan. Ref {ref}.",
        "sn": "SafePass: Pamuviri pamasuru — enda kune ese maANC uye tevera hurongwa hwekuzvara. Ref {ref}.",
        "nd": "SafePass: Ukukhulelwa okubili — vakashela zonke izivakashi ze-ANC ulandele uhlelo lokuzala. Ref {ref}.",
    },
    "followup_first_pregnancy": {
        "en": "SafePass: First pregnancy — attend all ANC visits and prepare your birth plan early. Ref {ref}.",
        "sn": "SafePass: Pamuviri rekutanga — enda kune ese maANC uye gadzirira hurongwa hwekuzvara. Ref {ref}.",
        "nd": "SafePass: Ukukhulelwa kokuqala — vakashela zonke izivakashi ze-ANC ulungiselele uhlelo lokuzala. Ref {ref}.",
    },
}

# Weekly education milestones (week -> message key)
EDUCATION_WEEKS = [12, 20, 28, 32, 36, 38, 40]

EDUCATION = {
    12: {
        "en": "SafePass Education (Week 12): Attend your antenatal visit. Take iron tablets. Ref {ref}.",
        "sn": "SafePass (Svondo 12): Enda kunoona nhumbu. Tora mapiritsi eropa. Ref {ref}.",
        "nd": "SafePass (Iviki 12): Iya otholakala ukukhulelwa. Thatha amathembu e-iron. Ref {ref}.",
    },
    20: {
        "en": "SafePass Education (Week 20): Know danger signs — bleeding, severe headache, swelling. Ref {ref}.",
        "sn": "SafePass (Svondo 20): Ziva chiratidzo — ropa, mutwe unorwadza, kuvava. Ref {ref}.",
        "nd": "SafePass (Iviki 20): Yazi uphawu — ukuphuma kwegazi, isihloko esibuhlungu, ukuvuvuka. Ref {ref}.",
    },
    28: {
        "en": "SafePass Education (Week 28): Plan transport & savings (US$5-10) for delivery. Ref {ref}.",
        "sn": "SafePass (Svondo 28): Ronga zvekufambisa & mari yekukurumidza ($5-10). Ref {ref}.",
        "nd": "SafePass (Iviki 28): Hlela ukuthutha & imali yokusiza ($5-10). Ref {ref}.",
    },
    32: {
        "en": "SafePass Education (Week 32): Identify birth escort & nearest hospital. Ref {ref}.",
        "sn": "SafePass (Svondo 32): Sarudza anokubatsira & chipatara chiri pedyo. Ref {ref}.",
        "nd": "SafePass (Iviki 32): Khetha umuntu ozokusiza & isibhedlela esiseduze. Ref {ref}.",
    },
    36: {
        "en": "SafePass Education (Week 36): Pack hospital bag. Sleep on your side. Ref {ref}.",
        "sn": "SafePass (Svondo 36): Ronga bag yechipatara. Gonera padivi. Ref {ref}.",
        "nd": "SafePass (Iviki 36): Lungiselela ingxowa yesibhedlela. Lala ohlangothini. Ref {ref}.",
    },
    38: {
        "en": "SafePass Education (Week 38): Watch for labour signs. Keep clinic number ready. Ref {ref}.",
        "sn": "SafePass (Svondo 38): Tarisa zviratidzo zvekuzvara. Chengeta nhamba yechipatara. Ref {ref}.",
        "nd": "SafePass (Iviki 38): Bheka uphawu lokuqala ukuhlaza. Gcina inombolo yesibhedlela. Ref {ref}.",
    },
    40: {
        "en": "SafePass Education (Week 40): Your due date is near. Go to facility if waters break or bleeding. Ref {ref}.",
        "sn": "SafePass (Svondo 40): Zuva rekuzvara rapedyo. Enda kuchipatara kana mvura yabuda kana ropa. Ref {ref}.",
        "nd": "SafePass (Iviki 40): Usuku lokuzala luseduze. Iya esibhedlela uma amanzi aphuma noma kukho igazi. Ref {ref}.",
    },
}

DANGER_SIGN_LABELS = {
    "bleeding": {"en": "bleeding", "sn": "ropa", "nd": "ukuphuma kwegazi"},
    "severe_headache": {"en": "severe headache", "sn": "mutwe unorwadza", "nd": "isihloko esibuhlungu"},
    "swelling": {"en": "swelling", "sn": "kuvava", "nd": "ukuvuvuka"},
    "reduced_movement": {"en": "reduced fetal movement", "sn": "mwana asisamira", "nd": "ukunyakaza komntwana kunciphile"},
    "other": {"en": "other concern", "sn": "chimwe", "nd": "okunye"},
}
