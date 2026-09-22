# -*- coding: utf-8 -*-
"""داده‌های ربات: لیست تیم‌ها، پرچم‌ها و کلمات کلیدی.

هر خط تیم:  نام نمایشی|نام دیگر|نام دیگر|...;پرچم;مهم(1/0)
- نام اول همان چیزی است که در پست روبیکا نوشته می‌شود.
- بقیه نام‌ها (فارسی، عربی، انگلیسی) فقط برای تشخیص هستند.
- فاصله و نیم‌فاصله مهم نیست («اتلتیکومادرید» = «اتلتیکو مادرید»).
- مهم=1 یعنی تیم بزرگ (برای ترتیب تیم‌ها در بازی مساوی).
برای افزودن تیم جدید فقط یک خط به لیست اضافه کن.
"""

ES = "\U0001F1EA\U0001F1F8"
EN = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"
IT = "\U0001F1EE\U0001F1F9"
DE = "\U0001F1E9\U0001F1EA"
FR = "\U0001F1EB\U0001F1F7"
IR = "\U0001F1EE\U0001F1F7"
PT = "\U0001F1F5\U0001F1F9"
NL = "\U0001F1F3\U0001F1F1"
TR = "\U0001F1F9\U0001F1F7"
SA = "\U0001F1F8\U0001F1E6"
EU = "\U0001F1EA\U0001F1FA"
ASIA = "\U0001F30F"

TEAM_LINES = f"""
بارسلونا|بارسا|barcelona|barca|fc barcelona|برشلونة|برشلونه;{ES};1
رئال مادرید|ریال مادرید|رآل مادرید|real madrid|ريال مدريد|ریال|رئال;{ES};1
اتلتیکو مادرید|اتلتیکو|atletico madrid|atletico|أتلتيكو مدريد|اتلتيكو مدريد;{ES};1
اتلتیک بیلبائو|بیلبائو|athletic bilbao|athletic club|أتلتيك بلباو;{ES};0
ویارئال|ویارآل|ویارال|villarreal|فياريال;{ES};0
رئال بتیس|بتیس|real betis|betis|ريال بيتيس;{ES};0
رئال سوسیداد|سوسیداد|real sociedad|ريال سوسيداد;{ES};0
سویا|سویّا|sevilla|إشبيلية|اشبیلیه;{ES};0
والنسیا|valencia|فالنسيا;{ES};0
سلتاویگو|سلتا ویگو|celta vigo|celta|سلتا فيغو;{ES};0
اوساسونا|osasuna|أوساسونا;{ES};0
ختافه|getafe|خيتافي;{ES};0
ژیرونا|girona|جيرونا;{ES};0
رایو وایکانو|rayo vallecano|رايو فايكانو;{ES};0
مایورکا|mallorca|ريال مايوركا;{ES};0
اسپانیول|espanyol|إسبانيول;{ES};0
آلاوس|alaves|ألافيس;{ES};0
التچه|الچه|elche|إلتشي;{ES};0
لوانته|levante|ليفانتي;{ES};0
اوندو|رئال اوندو|real oviedo|oviedo|ريال أوفييدو;{ES};0
ریسینگ|ریسینگ سانتاندر|racing santander|racing|راسينغ;{ES};0
آرسنال|arsenal|أرسنال;{EN};1
منچستر سیتی|من سیتی|manchester city|man city|مانشستر سيتي;{EN};1
منچستر یونایتد|من یونایتد|manchester united|man united|man utd|مانشستر يونايتد;{EN};1
لیورپول|liverpool|ليفربول;{EN};1
چلسی|chelsea|تشيلسي;{EN};1
تاتنهام|tottenham|spurs|توتنهام;{EN};1
نیوکاسل|newcastle|نيوكاسل;{EN};0
استون ویلا|aston villa|أستون فيلا;{EN};0
وستهام|وست هام|west ham|وست هام;{EN};0
برایتون|brighton|برايتون;{EN};0
برنتفورد|brentford|برينتفورد;{EN};0
فولام|fulham|فولهام;{EN};0
کریستال پالاس|crystal palace|كريستال بالاس;{EN};0
اورتون|everton|إيفرتون;{EN};0
ولوز|ولورهمپتون|wolves|wolverhampton|وولفرهامبتون;{EN};0
ناتینگهام فارست|ناتینگهام|nottingham forest|نوتنغهام فورست;{EN};0
بورنموث|bournemouth|بورنموث;{EN};0
لیدز یونایتد|لیدز|leeds united|leeds|ليدز يونايتد;{EN};0
برنلی|burnley|بيرنلي;{EN};0
ساندرلند|sunderland|سندرلاند;{EN};0
لسترسیتی|لستر سیتی|لستر|leicester city|leicester;{EN};0
ساوتهمپتون|southampton;{EN};0
ایپسویچ|ipswich;{EN};0
اینتر|اینترمیلان|اینتر میلان|inter milan|inter|إنتر ميلان|انتر ميلان;{IT};1
میلان|آ ث میلان|ای سی میلان|ac milan|milan|ميلان;{IT};1
یوونتوس|juventus|juve|يوفنتوس;{IT};1
ناپولی|napoli|نابولي;{IT};1
رم|آ اس رم|as roma|roma|روما;{IT};1
لاتزیو|lazio|لاتسيو;{IT};0
آتالانتا|atalanta|أتالانتا;{IT};0
فیورنتینا|fiorentina|فيورنتينا;{IT};0
بولونیا|bologna|بولونيا;{IT};0
تورینو|torino|تورينو;{IT};0
اودینزه|udinese|أودينيزي;{IT};0
جنوا|genoa|جنوى;{IT};0
کالیاری|cagliari|كالياري;{IT};0
کومو|como|كومو;{IT};0
پارما|parma|بارما;{IT};0
لچه|lecce|ليتشي;{IT};0
ورونا|هلاس ورونا|verona|hellas verona;{IT};0
کرمونزه|cremonese;{IT};0
پیزا|pisa;{IT};0
بایرن مونیخ|بایرن|bayern munich|bayern|بايرن ميونخ;{DE};1
دورتموند|بروسیا دورتموند|borussia dortmund|dortmund|دورتموند;{DE};1
بایرلورکوزن|لورکوزن|bayer leverkusen|leverkusen|ليفركوزن;{DE};1
لایپزیگ|rb leipzig|leipzig|لايبزيغ;{DE};0
اشتوتگارت|stuttgart|شتوتغارت;{DE};0
آینتراخت فرانکفورت|فرانکفورت|eintracht frankfurt|frankfurt|فرانكفورت;{DE};0
فرایبورگ|freiburg|فرايبورغ;{DE};0
هوفنهایم|hoffenheim|هوفنهايم;{DE};0
ولفسبورگ|wolfsburg|فولفسبورغ;{DE};0
بوروسیا مونشن گلادباخ|گلادباخ|gladbach|monchengladbach|مونشنغلادباخ;{DE};0
ماینتس|mainz|ماينتس;{DE};0
اوگسبورگ|augsburg|أوغسبورغ;{DE};0
اونیون برلین|union berlin|أونيون برلين;{DE};0
وردر برمن|werder bremen|فيردر بريمن;{DE};0
هایدنهایم|heidenheim;{DE};0
سنت پائولی|st pauli|سانت باولي;{DE};0
کلن|köln|koln|cologne;{DE};0
هامبورگ|hamburg|hamburger sv;{DE};0
پاری سن ژرمن|پاریس سن ژرمن|پی اس جی|psg|paris saint-germain|paris saint germain|باريس سان جيرمان;{FR};1
مارسی|marseille|مارسيليا;{FR};0
لیون|lyon|ليون;{FR};0
موناکو|monaco|موناكو;{FR};0
لیل|lille|ليل;{FR};0
نیس|nice|نيس;{FR};0
لنس|lens|لانس;{FR};0
رن|رنس|rennes|رين;{FR};0
استراسبورگ|strasbourg|ستراسبورغ;{FR};0
نانت|nantes|نانت;{FR};0
تولوز|toulouse|تولوز;{FR};0
برست|brest|بريست;{FR};0
اوسر|auxerre;{FR};0
آنژه|angers;{FR};0
لوهاور|le havre;{FR};0
لوریان|lorient;{FR};0
متز|metz;{FR};0
پرسپولیس|persepolis|برسبوليس;{IR};1
استقلال|esteghlal|استقلال تهران|الاستقلال;{IR};1
سپاهان|sepahan|سباهان;{IR};1
تراکتور|تراکتورسازی|tractor|traktor;{IR};1
فولاد|فولاد خوزستان|foolad;{IR};0
گل گهر|گلگهر|gol gohar|golgohar;{IR};0
ملوان|malavan;{IR};0
نساجی|نساجی مازندران|nassaji;{IR};0
ذوب آهن|zob ahan;{IR};0
استقلال خوزستان|esteghlal khuzestan;{IR};0
آلومینیوم|آلومینیوم اراک|aluminium arak;{IR};0
صنعت نفت|sanat naft;{IR};0
چادرملو|chadormalu;{IR};0
هوادار|havadar;{IR};0
پیکان|paykan;{IR};0
خیبر|kheybar;{IR};0
بنفیکا|benfica|بنفيكا;{PT};0
پورتو|porto|بورتو;{PT};0
اسپورتینگ لیسبون|اسپورتینگ|sporting cp|sporting lisbon|سبورتينغ لشبونة;{PT};0
آژاکس|ajax|أياكس;{NL};0
پی اس وی|psv|آیندهوون|eindhoven|بي إس في;{NL};0
فاینورد|feyenoord|فينورد;{NL};0
گالاتاسرای|galatasaray|غلطة سراي;{TR};0
فنرباغچه|fenerbahce|فنربخشة;{TR};0
بشیکتاش|besiktas|بشيكتاش;{TR};0
النصر|al nassr|al-nassr|النصر;{SA};1
الهلال|al hilal|al-hilal|الهلال;{SA};1
الاتحاد|al ittihad|al-ittihad|الاتحاد;{SA};0
الاهلی عربستان|al ahli|al-ahli|الأهلي السعودي;{SA};0
اینتر میامی|inter miami;;1
سلتیک|celtic;;0
کلوب بروژ|club brugge|بروژ;;0
شاختار|شاختار دونتسک|shakhtar;;0
ایران|iran|team melli|منتخب إيران|ايران;;1
عراق|iraq|العراق;;0
عربستان|saudi arabia|السعودية;;0
ژاپن|japan|اليابان;;0
کره جنوبی|korea republic|south korea|كوريا الجنوبية;;0
قطر|qatar|قطر;;0
امارات|uae|الإمارات;;0
ازبکستان|uzbekistan;;0
استرالیا|australia;;0
آرژانتین|argentina|الأرجنتين;;1
برزیل|brazil|البرازيل;;1
اروگوئه|uruguay;;0
کلمبیا|colombia;;0
فرانسه|france|فرنسا;;1
اسپانیا|spain|إسبانيا;;1
آلمان|germany|ألمانيا;;1
انگلیس|انگلستان|england|إنجلترا;;1
پرتغال|portugal|البرتغال;;1
ایتالیا|italy|إيطاليا;;1
هلند|netherlands|holland|هولندا;;1
بلژیک|belgium|بلجيكا;;0
کرواسی|croatia|كرواتيا;;0
مراکش|morocco|المغرب;;0
سنگال|senegal;;0
مصر|egypt|مصر;;0
آمریکا|usa|united states|أمريكا;;0
مکزیک|mexico|المكسيك;;0
ترکیه|turkey|turkiye|تركيا;;0
"""

FLAG_HINTS = [
    (r"لیگ\s*قهرمانان\s*اروپا|champions\s*league|لیگ\s*اروپا|europa|کنفرانس\s*لیگ|یورو\s*۲|euro\s*20", EU),
    (r"لیگ\s*قهرمانان\s*آسیا|\bacl\b|جام\s*جهانی|world\s*cup|انتخابی|جام\s*ملت", ASIA),
    (r"لالیگا|la\s*liga", ES),
    (r"لیگ\s*برتر\s*انگلیس|premier\s*league|اف\s*ای\s*کاپ|جام\s*حذفی\s*انگلیس", EN),
    (r"سری\s*آ|serie\s*a", IT),
    (r"بوندس\s*لیگا|bundesliga", DE),
    (r"لیگ\s*۱|ligue\s*1", FR),
    (r"لیگ\s*برتر\s*ایران|لیگ\s*خلیج\s*فارس|جام\s*حذفی\s*ایران", IR),
]

ORDINALS = {
    "اول": 1, "دوم": 2, "سوم": 3, "چهارم": 4, "پنجم": 5,
    "ششم": 6, "هفتم": 7, "هشتم": 8, "نهم": 9, "دهم": 10,
}
