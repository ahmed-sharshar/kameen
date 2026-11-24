/* Kameen interface language: English (default) or Arabic.

   This file only swaps the words on screen. It never changes what a page does: no page script reads
   it, and it reads nothing the pages rely on. It watches the page, replaces known English interface
   text with Arabic (including text the pages add later), flips the layout right-to-left, and puts
   the original English back when the visitor switches again.

   Never translated: conversation messages, captured intel and quotes, drill lessons (they are in the
   language the drill was run in), anything a person typed, and codes, numbers and links. */
(function () {
  'use strict';

  var KEY = 'kameen_lang';
  var lang = 'en';
  try { lang = localStorage.getItem(KEY) === 'ar' ? 'ar' : 'en'; } catch (e) { /* storage blocked */ }

  function applyDirection() {
    var root = document.documentElement;
    root.setAttribute('lang', lang === 'ar' ? 'ar' : 'en');
    root.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
  }
  applyDirection();                      /* before first paint, so the page does not jump */

  /* ------------------------------------------------------------ exact interface strings */
  var AR = {
    /* shared: top bar, status */
    'Waking up Kameen...': 'جارٍ تشغيل كمين...',
    'Ready': 'جاهز',
    'Server not reachable': 'تعذّر الوصول إلى الخادم',
    'Sections': 'الأقسام',
    'Play the scammer': 'العب دور المحتال',
    'Test yourself': 'اختبر نفسك',
    'Dashboard': 'لوحة المتابعة',
    'Play the scammer - Kameen': 'العب دور المحتال - كمين',
    'Test yourself - Kameen': 'اختبر نفسك - كمين',
    'Dashboard - Kameen': 'لوحة المتابعة - كمين',
    'The server did not answer. Reload the page to try again.': 'لم يستجب الخادم. أعد تحميل الصفحة للمحاولة مجددًا.',
    'Could not reach the server. Check the connection and try again.': 'تعذّر الوصول إلى الخادم. تحقق من الاتصال وحاول مجددًا.',
    'Live connection lost. Reconnecting...': 'انقطع الاتصال المباشر. جارٍ إعادة الاتصال...',

    /* landing page */
    'An ambush for phone and message scams. One AI agent with two jobs: it answers scammers as a believable victim and keeps them talking, or it plays the scammer so people can practise saying no.':
      'كمينٌ لعمليات الاحتيال عبر الهاتف والرسائل. وكيل ذكاء اصطناعي واحد بمهمتين: يرد على المحتالين بوصفه ضحية مقنعة ويُبقيهم في المحادثة، أو يلعب دور المحتال ليتدرّب الناس على الرفض.',
    'This is a simulation. You play the scammer or the trainee. Drill secrets are masked before storage.':
      'هذه محاكاة. أنت تلعب دور المحتال أو المتدرّب، وتُخفى أي معلومة سرية في التمارين قبل حفظها.',
    'Enter the access code': 'أدخل رمز الدخول',
    'Access code': 'رمز الدخول',
    'Unlock': 'دخول',
    'Choose a mode': 'اختر وضعًا',
    'Kameen plays the victim': 'كمين يلعب دور الضحية',
    'You play the scammer': 'أنت تلعب دور المحتال',
    'Write or call as a scammer. Kameen answers as Rajesh, Sara or Abu Khalid, stalls you, and collects every account number, phone number and link you give away.':
      'راسِل أو اتصل بصفتك محتالًا. يرد كمين بشخصية راجيش أو سارة أو أبو خالد، ويماطلك، ويلتقط كل رقم حساب أو هاتف أو رابط تكشفه.',
    'Open the decoy': 'افتح الطُّعم',
    'Kameen plays the scammer': 'كمين يلعب دور المحتال',
    'You are the trainee': 'أنت المتدرّب',
    'With your consent, Kameen runs a scam on you. It stops before you share anything real and shows you what to watch for.':
      'بموافقتك، ينفّذ كمين محاولة احتيال عليك، ويتوقف قبل أن تشارك أي معلومة حقيقية، ثم يريك ما يجب الانتباه إليه.',
    'Start a drill': 'ابدأ تمرينًا',
    'Open the dashboard': 'افتح لوحة المتابعة',
    'Sessions, linked campaigns, drill results and test evidence.': 'الجلسات والحملات المترابطة ونتائج التمارين ونتائج الاختبار.',
    'Use a different code': 'استخدم رمزًا آخر',
    'Sample exchange': 'مثال على محادثة',
    'Your parcel is on hold. Pay the AED 12 customs fee today or it goes back.':
      'طردك محتجز. ادفع رسوم الجمارك البالغة 12 درهمًا اليوم وإلا أُعيد إلى المرسِل.',
    'Oh no, that is my mother\'s medicine. I can pay now. My card is not working, can I do bank transfer?':
      'يا إلهي، هذا دواء والدتي. أستطيع الدفع الآن، لكن بطاقتي لا تعمل، هل يمكنني التحويل البنكي؟',
    'Yes. Send to AE07 0331 2345 6789 0123 456': 'نعم. حوّل إلى AE07 0331 2345 6789 0123 456',
    'Send to AE07 0331 2345 6789 0123 456': 'حوّل إلى AE07 0331 2345 6789 0123 456',
    'One minute sir, I am writing it down. Which name is on the account?': 'لحظة يا سيدي، أكتبه الآن. ما الاسم المسجّل على الحساب؟',
    'A sample exchange. Every detail in it is made up.': 'مثال على محادثة، وكل تفاصيلها مختلَقة.',
    'That code was not accepted. Check it and try again.': 'لم يُقبل هذا الرمز. تحقق منه وحاول مجددًا.',
    'Enter the access code.': 'أدخل رمز الدخول.',
    'Kameen is still waking up, which can take a minute. Your code will be checked as soon as it is ready.':
      'ما زال كمين قيد التشغيل، وقد يستغرق ذلك دقيقة. سيُتحقق من رمزك فور جاهزيته.',

    /* decoy page */
    'Pick who answers, then try to scam them. Kameen stalls you and notes what you give away.':
      'اختر مَن يرد، ثم حاول الاحتيال عليه. يماطلك كمين ويسجّل ما تكشفه.',
    'Who answers': 'مَن يرد',
    'Loading personas...': 'جارٍ تحميل الشخصيات...',
    'Looks like': 'شكل المحادثة',
    'SMS': 'رسالة نصية',
    'WhatsApp': 'واتساب',
    'Email': 'بريد إلكتروني',
    'Text message': 'رسالة نصية',
    'Start text session': 'ابدأ جلسة نصية',
    'Start call': 'ابدأ مكالمة',
    'Conversation': 'المحادثة',
    'Victim': 'الضحية',
    'Call': 'مكالمة',
    'Hang up': 'إنهاء المكالمة',
    'Messages': 'الرسائل',
    'Your message as the scammer': 'رسالتك بصفتك المحتال',
    'Write as the scammer': 'اكتب بصفتك المحتال',
    'Send': 'إرسال',
    'How believable was the victim? One line.': 'ما مدى إقناع الضحية؟ في سطر واحد.',
    'Send rating': 'إرسال التقييم',
    'What Kameen has learned': 'ما عرفه كمين',
    'Stage': 'المرحلة',
    'Not started': 'لم تبدأ',
    'Starting': 'جارٍ البدء',
    'Intel cards': 'بطاقات المعلومات',
    'Account numbers, phone numbers and links the scammer gives away appear here.': 'تظهر هنا أرقام الحسابات والهواتف والروابط التي يكشفها المحتال.',
    'Guardrail events': 'أحداث الحماية',
    'None so far.': 'لا شيء حتى الآن.',
    'Canaries handed out': 'بيانات الطُّعم المقدَّمة',
    'Fake, tracked values the victim gave the scammer.': 'قيم وهمية متتبَّعة قدّمتها الضحية للمحتال.',
    'End session': 'إنهاء الجلسة',
    'Evidence pack': 'حزمة الأدلة',
    'From you': 'منك',
    'the victim': 'الضحية',
    'Session ended': 'انتهت الجلسة',
    'Pick who answers first.': 'اختر مَن يرد أولًا.',
    'Call ended. The session is still open: write, or end it.': 'انتهت المكالمة. ما زالت الجلسة مفتوحة: اكتب، أو أنهِها.',
    'Write one line first.': 'اكتب سطرًا واحدًا أولًا.',
    'Rating sent. Thank you.': 'أُرسل التقييم. شكرًا لك.',
    'The server has no personas yet.': 'لا توجد شخصيات على الخادم بعد.',
    'Pick who answers and start a session. In text, you write first.': 'اختر مَن يرد وابدأ جلسة. في المحادثة النصية تبدأ أنت بالكتابة.',
    'Typing': 'يكتب',

    /* drill page */
    'Kameen will play a scammer and try to trick you. It stops before you share anything real, then shows you what to watch for.':
      'سيلعب كمين دور المحتال ويحاول خداعك، ويتوقف قبل أن تشارك أي معلومة حقيقية، ثم يريك ما يجب الانتباه إليه.',
    'Nickname': 'اسم مستعار',
    'Group or department': 'المجموعة أو الإدارة',
    'I agree to take part in a simulated scam drill': 'أوافق على المشاركة في تمرين احتيال محاكى',
    'Use a nickname, not your full name. Anything that looks like a secret is masked before it is stored.':
      'استخدم اسمًا مستعارًا لا اسمك الكامل. ويُخفى كل ما يشبه معلومة سرية قبل حفظه.',
    'Enrol and continue': 'سجّل وتابع',
    'Pick a drill': 'اختر تمرينًا',
    'Enrol someone else': 'سجّل شخصًا آخر',
    'Scenario': 'السيناريو',
    'Loading scenarios...': 'جارٍ تحميل السيناريوهات...',
    'How it reaches you': 'طريقة الوصول إليك',
    'Text': 'نص',
    'Voice and language': 'الصوت واللغة',
    'English': 'الإنجليزية',
    'Indian English': 'الإنجليزية بلكنة هندية',
    'Arabic': 'العربية',
    'Emirati Arabic': 'العربية الإماراتية',
    'Arabic runs the whole drill in Arabic, in text or on a call.': 'عند اختيار العربية يجري التمرين كاملًا بالعربية، نصًا أو في مكالمة.',
    'Start drill': 'ابدأ التمرين',
    'The server refused this drill': 'رفض الخادم هذا التمرين',
    'Consent is checked by the server': 'الخادم هو من يتحقق من الموافقة',
    'A drill only starts for someone who enrolled. This button asks for a drill with no enrolment, so you can see the refusal.':
      'لا يبدأ التمرين إلا لمن سجّل. يطلب هذا الزر تمرينًا دون تسجيل، لترى الرفض بنفسك.',
    'Try to drill someone who is not enrolled': 'جرّب تمرينًا لشخص غير مسجَّل',
    'Refused by the server': 'رفضه الخادم',
    'Drill': 'تمرين',
    'This was a Kameen safety drill': 'كان هذا تمرين سلامة من كمين',
    'Red flags in this conversation': 'العلامات التحذيرية في هذه المحادثة',
    'How to report a real one': 'كيف تبلّغ عن محاولة حقيقية',
    'Try another scenario': 'جرّب سيناريو آخر',
    'Back to the start': 'العودة إلى البداية',
    'Unknown sender': 'مرسِل مجهول',
    'Your reply': 'ردّك',
    'Reply': 'اكتب ردّك',
    'Stop the drill': 'إيقاف التمرين',
    'Reply as you normally would. You can stop at any time.': 'رد كما تفعل عادةً، ويمكنك التوقف في أي وقت.',
    'You resisted': 'قاومت',
    'You hesitated': 'تردّدت',
    'You were about to go along with it': 'كنت على وشك الاستجابة',
    'You started to share a secret': 'بدأت بمشاركة معلومة سرية',
    'We stopped the drill early': 'أوقفنا التمرين مبكرًا',
    'You are enrolled. Pick a scenario and how it reaches you.': 'أنت مسجَّل. اختر سيناريو وطريقة وصوله إليك.',
    'No approved scenarios yet. A scenario must be approved before it can be used in a drill.':
      'لا توجد سيناريوهات معتمدة بعد. يجب اعتماد السيناريو قبل استخدامه في أي تمرين.',
    '1 more scenario is waiting for approval and cannot be used yet.': 'هناك سيناريو آخر بانتظار الاعتماد ولا يمكن استخدامه بعد.',
    'Enter a nickname.': 'أدخل اسمًا مستعارًا.',
    'Enter your group or department.': 'أدخل مجموعتك أو إدارتك.',
    'Tick the box to agree before you continue.': 'ضع علامة في المربع للموافقة قبل المتابعة.',
    'The server did not return an enrolment.': 'لم يُرجع الخادم سجل التسجيل.',
    'Pick a scenario first.': 'اختر سيناريو أولًا.',
    'Connecting the call. Answer as you normally would.': 'جارٍ توصيل المكالمة. أجب كما تفعل عادةً.',
    'Waiting for the first message.': 'بانتظار الرسالة الأولى.',
    'Call ended. The drill is still open: reply by text, or stop it.': 'انتهت المكالمة. ما زال التمرين مفتوحًا: رد كتابيًا، أو أوقفه.',
    'Ended by you': 'أنهيتها أنت',
    'Drill ended': 'انتهى التمرين',
    'You stopped the drill': 'أوقفت التمرين',
    'The server started a drill without an enrolment. That should not happen: the session was ended.':
      'بدأ الخادم تمرينًا دون تسجيل، وهذا لا يُفترض أن يحدث: أُنهيت الجلسة.',
    'Test by email or phone': 'الاختبار عبر البريد أو الهاتف',
    'The same drill can reach people as a simulated phishing email or as a voice call. Use your own address or number to try it on yourself, or a list of people who agreed to be tested.':
      'يمكن أن يصل التمرين نفسه إلى الناس في صورة رسالة تصيّد محاكاة أو مكالمة صوتية. استخدم عنوانك أو رقمك لتجربته على نفسك، أو قائمة بأشخاص وافقوا على أن يُختبروا.',
    'Phishing-awareness emails': 'رسائل التوعية بالتصيّد الاحتيالي',
    'Send a simulated scam email to people you are authorised to test. The one link in it lands on a Kameen page that records the click and immediately teaches — there is no login form and nothing is collected. The emails never imitate a real bank or company. Who clicked shows on the dashboard.':
      'أرسل رسالة احتيال محاكاة إلى أشخاص مخوَّل باختبارهم. يقود الرابط الوحيد فيها إلى صفحة من كمين تسجّل النقرة وتقدّم الدرس فورًا — لا يوجد نموذج لتسجيل الدخول ولا يُجمع أي شيء. ولا تنتحل الرسائل صفة أي بنك أو شركة حقيقية، ويظهر مَن نقر الرابط في لوحة المتابعة.',
    'A different one for each person': 'سيناريو مختلف لكل شخص',
    'A different one each': 'سيناريو مختلف لكل شخص',
    'Language': 'اللغة',
    'Authorised by (your name)': 'المخوِّل (اسمك)',
    'Recipients — one per line, as': 'المستلمون — واحد في كل سطر، بصيغة',
    'or just an email': 'أو عنوان البريد فقط',
    'I confirm these people have agreed to receive security-awareness tests, and I am authorised to send them.':
      'أؤكد أن هؤلاء الأشخاص وافقوا على تلقي اختبارات التوعية الأمنية، وأنني مخوَّل بإرسالها إليهم.',
    'Send awareness emails': 'إرسال رسائل التوعية',
    'Awareness calls by phone': 'مكالمات التوعية الهاتفية',
    'Call a consented number and run a drill by voice. Kameen dials through ElevenLabs and plays the scenario in the chosen voice; it stops before any secret is given and reveals the drill, like every other channel. Only call people who agreed to be tested.':
      'اتصل برقم وافق صاحبه ونفّذ تمرينًا صوتيًا. يتصل كمين عبر ElevenLabs ويؤدي السيناريو بالصوت المختار، ويتوقف قبل الإفصاح عن أي معلومة سرية ثم يكشف التمرين، كما في كل القنوات. لا تتصل إلا بمن وافق على أن يُختبر.',
    'Phone number (international, e.g. +9715XXXXXXXX)': 'رقم الهاتف (بالصيغة الدولية، مثل ‎+9715XXXXXXXX)',
    'Voice': 'الصوت',
    'I confirm this person agreed to receive a security-awareness call, and I am authorised to call them.':
      'أؤكد أن هذا الشخص وافق على تلقي مكالمة توعية أمنية، وأنني مخوَّل بالاتصال به.',
    'Place the call': 'إجراء المكالمة',
    'Email sending is not set up. Add a Resend API key on the server to send awareness emails.':
      'إرسال البريد غير مُعدّ. أضف مفتاح خدمة البريد على الخادم لإرسال رسائل التوعية.',
    'the configured address': 'العنوان المُعدّ',
    'Enter a group or department.': 'أدخل مجموعة أو إدارة.',
    'Enter at least one recipient.': 'أدخل مستلمًا واحدًا على الأقل.',
    'Please confirm you are authorised to test these people.': 'يرجى تأكيد أنك مخوَّل باختبار هؤلاء الأشخاص.',
    'Phone calls are not set up. Add the ElevenLabs API key and an imported Twilio number ID on the server.':
      'المكالمات الهاتفية غير مُعدّة. أضف مفتاح ElevenLabs ومعرّف رقم Twilio على الخادم.',
    'Enter the number in international format, like +971500000000.': 'أدخل الرقم بالصيغة الدولية، مثل ‎+971500000000.',
    'Please confirm you are authorised to call this person.': 'يرجى تأكيد أنك مخوَّل بالاتصال بهذا الشخص.',
    'no response': 'لا استجابة',

    /* dashboard */
    'Dashboard sections': 'أقسام لوحة المتابعة',
    'Overview': 'نظرة عامة',
    'Sessions': 'الجلسات',
    'Campaigns': 'الحملات',
    'Drills': 'التمارين',
    'Cases': 'القضايا',
    'Evidence': 'نتائج الاختبار',
    'Everything Kameen has run, across every channel: how many people were tested, how many were caught out, and where the risk is.':
      'كل ما نفّذه كمين عبر جميع القنوات: كم شخصًا اختُبر، وكم منهم وقع في الفخ، وأين يكمن الخطر.',
    'Refresh': 'تحديث',
    'People caught out, by channel': 'مَن وقعوا في الفخ بحسب القناة',
    'The donut shows which channels the caught-out people came from. The bars show each channel\'s risk rate — the share of attempts there where the person was about to hand over a secret or clicked the phishing link — so the riskiest channel stands out.':
      'يبيّن المخطط الدائري القنوات التي جاء منها مَن وقعوا في الفخ، وتبيّن الأشرطة نسبة الخطر في كل قناة — أي نسبة المحاولات التي كان فيها الشخص على وشك تسليم معلومة سرية أو نقر رابط التصيّد — فتبرز القناة الأخطر.',
    'Loading…': 'جارٍ التحميل…',
    'How drills ended': 'كيف انتهت التمارين',
    'Red flags people miss most': 'العلامات التحذيرية الأكثر إغفالًا',
    'No missed flags recorded yet.': 'لم تُسجَّل علامات مُغفلة بعد.',
    'At risk, by scenario': 'الخطر بحسب السيناريو',
    'At risk': 'معرّضون للخطر',
    'At risk, by group': 'الخطر بحسب المجموعة',
    'Group': 'المجموعة',
    'People who clicked a phishing link': 'الأشخاص الذين نقروا رابط تصيّد',
    'Email is the one channel where a person can be named — the link records who clicked. Drills are counted by group only, so no one is singled out.':
      'البريد الإلكتروني هو القناة الوحيدة التي يمكن فيها تسمية الشخص، لأن الرابط يسجّل مَن نقره. أما التمارين فتُحتسب بحسب المجموعة فقط، فلا يُميَّز أحد.',
    'Name': 'الاسم',
    'When': 'الوقت',
    'Every decoy and drill session, newest first. The list updates every 5 seconds. Select a row to open it.':
      'كل جلسات الطُّعم والتمارين، الأحدث أولًا. تتحدّث القائمة كل 5 ثوانٍ. اختر صفًا لفتحه.',
    'Started': 'البدء',
    'Mode': 'الوضع',
    'Persona or scenario': 'الشخصية أو السيناريو',
    'Channel': 'القناة',
    'Status': 'الحالة',
    'Turns': 'الدورات',
    'Intel': 'المعلومات',
    'Loading sessions...': 'جارٍ تحميل الجلسات...',
    'Close': 'إغلاق',
    'Transcript': 'نص المحادثة',
    'Nothing captured yet.': 'لم يُلتقط شيء بعد.',
    'Drill result': 'نتيجة التمرين',
    'Live events': 'الأحداث المباشرة',
    'Listening. New events for this session appear here.': 'في وضع الاستماع. تظهر هنا الأحداث الجديدة لهذه الجلسة.',
    'Sessions that share an account number, phone number or link are joined into one campaign.':
      'تُضمّ الجلسات التي تشترك في رقم حساب أو رقم هاتف أو رابط في حملة واحدة.',
    'Session': 'جلسة',
    'Intel item': 'معلومة',
    'Graph of sessions and the intel items they share': 'مخطط الجلسات والمعلومات المشتركة بينها',
    'Zoom in': 'تكبير',
    'Zoom out': 'تصغير',
    'Fit': 'ملاءمة',
    'Select a node to see what it is.': 'اختر عقدة لمعرفة ماهيّتها.',
    'Nothing to link yet. Campaigns appear once two sessions share the same intel.':
      'لا يوجد ما يُربط بعد. تظهر الحملات حين تشترك جلستان في المعلومة نفسها.',
    'How people did in drills. Results are counted by group, never by person.':
      'أداء الناس في التمارين. تُحتسب النتائج بحسب المجموعة، لا بحسب الأفراد أبدًا.',
    'By outcome': 'بحسب النتيجة',
    'By scenario': 'بحسب السيناريو',
    'By group': 'بحسب المجموعة',
    'Loading drill results...': 'جارٍ تحميل نتائج التمارين...',
    'Surprise drills by Telegram': 'التمارين المفاجئة عبر تيليجرام',
    'Share one link with a group. Each person who opens it reads what will happen and must reply AGREE. They then get one unmarked scam message at a moment they cannot predict, inside the window you choose. Only counts are shown here, never who.':
      'شارك رابطًا واحدًا مع المجموعة. يقرأ كل من يفتحه ما سيحدث، ويجب أن يرد بكلمة AGREE. ثم تصله رسالة احتيال واحدة غير معلَّمة في لحظة لا يتوقعها ضمن الفترة التي تختارها. لا تظهر هنا إلا الأعداد، دون أي أسماء.',
    'Send within': 'الإرسال خلال',
    '10 minutes (for a demo)': '10 دقائق (للعرض التجريبي)',
    '1 hour': 'ساعة واحدة',
    '8 hours': '8 ساعات',
    '1 day': 'يوم واحد',
    '3 days': '3 أيام',
    '7 days': '7 أيام',
    'Create invite link': 'إنشاء رابط دعوة',
    'Window': 'الفترة',
    'Joined': 'انضموا',
    'Waiting': 'بالانتظار',
    'Sent': 'أُرسلت',
    'Finished': 'اكتملت',
    'Invite link': 'رابط الدعوة',
    'Every drill and every phishing click opens a case — mirroring a handoff to Abu Dhabi Police (Aman) via TAMM, with the person\'s identity confirmed by UAE Pass. Each case is labelled':
      'يفتح كل تمرين وكل نقرة على رابط تصيّد قضيةً — محاكاةً لتسليمها إلى شرطة أبوظبي (خدمة أمان) عبر منصة «تم»، مع تأكيد هوية الشخص عبر UAE Pass. وتُصنَّف كل قضية',
    'Fooled': 'وقع في الفخ',
    'or': 'أو',
    'Not fooled': 'لم يقع في الفخ',
    '. A fooled case from the monitored number is emailed automatically; any other fooled case can be emailed to an address you choose. A not-fooled case needs no action.':
      '. وتُرسَل قضية الرقم المراقَب تلقائيًا بالبريد الإلكتروني إذا وقع صاحبها في الفخ، ويمكن إرسال أي قضية أخرى من هذا النوع إلى عنوان تختاره. أما القضية التي لم يقع صاحبها في الفخ فلا تحتاج إلى أي إجراء.',
    'Simulation only — not connected to TAMM, UAE Pass or the Aman service, which Kameen is not authorised to use. Every record is synthetic and no real case is filed. The case email is sent from this project\'s own name (ScamShield AI), never as the police, a bank or any other body.':
      'محاكاة فقط — غير متصلة بمنصة «تم» أو UAE Pass أو خدمة «أمان»، ولا يملك كمين تصريحًا باستخدامها. كل السجلات اصطناعية ولا تُرفع أي قضية حقيقية. وتُرسَل رسالة القضية باسم المشروع (ScamShield AI)، لا باسم الشرطة أو أي بنك أو جهة أخرى.',
    'Loading cases…': 'جارٍ تحميل القضايا…',
    'Results of the latest automated test run against Kameen.': 'نتائج أحدث تشغيل آلي للاختبارات على كمين.',
    'Loading test results...': 'جارٍ تحميل نتائج الاختبار...',
    'Text / web': 'نص / الموقع',
    'Phone call': 'مكالمة هاتفية',
    'Telegram': 'تيليجرام',
    'Email (phishing)': 'البريد (تصيّد)',
    'Nothing yet.': 'لا شيء بعد.',
    'People caught out': 'مَن وقعوا في الفخ',
    'across every channel': 'عبر كل القنوات',
    'Drills run': 'التمارين المنفّذة',
    'Phishing emails': 'رسائل التصيّد',
    'Scammers engaged': 'جلسات مع محتالين',
    'caught out': 'وقعوا في الفخ',
    'drills': 'تمرينًا',
    'No results on any channel yet.': 'لا نتائج على أي قناة بعد.',
    'No drills yet.': 'لا تمارين بعد.',
    'No group is large enough to show yet.': 'لا توجد مجموعة كبيرة بما يكفي لعرضها بعد.',
    'No one has clicked a phishing link yet.': 'لم ينقر أحد رابط تصيّد بعد.',
    'Decoy': 'طُعم',
    'No sessions yet. Start one from Play the scammer or Test yourself.': 'لا جلسات بعد. ابدأ جلسة من «العب دور المحتال» أو «اختبر نفسك».',
    'Kameen as the scammer': 'كمين بدور المحتال',
    'Kameen as the victim': 'كمين بدور الضحية',
    'Trainee': 'المتدرّب',
    'Scammer': 'المحتال',
    'No messages yet.': 'لا رسائل بعد.',
    'Loading session...': 'جارٍ تحميل الجلسة...',
    'Linked campaigns': 'الحملات المترابطة',
    'Sessions in the graph': 'الجلسات في المخطط',
    'Intel items': 'المعلومات',
    'The graph library did not load, so the graph cannot be drawn. The counts above are still correct.':
      'لم تُحمَّل مكتبة المخطط، لذا لا يمكن رسمه. والأعداد أعلاه صحيحة.',
    'Drills completed': 'التمارين المكتملة',
    'No drills have been completed yet.': 'لم يكتمل أي تمرين بعد.',
    'Copy link': 'نسخ الرابط',
    'Copied': 'نُسخ',
    'Copy this link': 'انسخ هذا الرابط',
    'Telegram is not connected yet. Add the bot token on the server to use surprise drills.':
      'تيليجرام غير متصل بعد. أضف رمز البوت على الخادم لاستخدام التمارين المفاجئة.',
    'No invites yet.': 'لا دعوات بعد.',
    'Not available': 'غير متاح',
    'Web / SMS': 'الموقع / رسالة نصية',
    'Fooled — set up email on the server (SMTP or a Resend key) to send the case details.': 'وقع في الفخ — أعدّ البريد على الخادم لإرسال تفاصيل القضية.',
    'email address': 'عنوان البريد الإلكتروني',
    'Email the case details to': 'إرسال تفاصيل القضية إلى',
    'Email case details': 'إرسال تفاصيل القضية',
    'Enter a valid email address.': 'أدخل عنوان بريد إلكتروني صحيحًا.',
    'Sending…': 'جارٍ الإرسال…',
    'Fooled — email the case details': 'وقع في الفخ — أرسل تفاصيل القضية',
    'Cases opened': 'القضايا المفتوحة',
    'no action': 'لا إجراء',
    'Clicked a phishing link': 'نقر رابط تصيّد',
    'Identity (UAE Pass, simulated)': 'الهوية (UAE Pass، محاكاة)',
    'Contact': 'وسيلة التواصل',
    'Scam type': 'نوع الاحتيال',
    'Caught on': 'القناة',
    'How it was flagged': 'كيفية الرصد',
    'Not fooled — no further action needed.': 'لم يقع في الفخ — لا حاجة إلى أي إجراء آخر.',
    'Emailed': 'أُرسلت بالبريد',
    'Open': 'مفتوحة',
    'No action': 'لا إجراء',
    'the awareness team': 'فريق التوعية',
    'No cases yet. A case opens for every drill and every phishing click.': 'لا قضايا بعد. تُفتح قضية لكل تمرين ولكل نقرة على رابط تصيّد.',
    'No test run uploaded yet': 'لم يُرفع أي تشغيل للاختبار بعد',
    'Pass': 'نجح',
    'Fail': 'لم ينجح',
    'Smaller groups (combined)': 'مجموعات أصغر (مجمّعة)',

    /* labels shared through app.js */
    'IBAN': 'آيبان',
    'Phone': 'هاتف',
    'Link': 'رابط',
    'Card': 'بطاقة',
    'Wallet': 'محفظة',
    'Bank': 'بنك',
    'Account': 'حساب',
    'OTP': 'رمز التحقق',
    'Unknown number in a reply': 'رقم غير معروف في ردّ',
    'Role leak caught': 'رُصد خروج عن الدور',
    'Agent asked for a secret': 'طلب الوكيل معلومة سرية',
    'Resisted': 'قاوم',
    'Hesitated': 'تردّد',
    'Would comply': 'كان سيستجيب',
    'Attempted disclosure': 'بدأ بالإفصاح',
    'Distress': 'ضيق',
    'Stopped': 'توقّف',
    'Ignored the message': 'تجاهل الرسالة',
    'Ignored': 'تجاهل',
    'Clicked': 'نقر الرابط',
    'The server did not return a session.': 'لم يُرجع الخادم جلسة.',
    'The voice module did not load.': 'لم تُحمَّل وحدة الصوت.',
    'Connecting...': 'جارٍ الاتصال...',
    'Microphone access was blocked. Allow it in the browser and try again.': 'حُظر الوصول إلى الميكروفون. اسمح به في المتصفح وحاول مجددًا.',
    'No microphone was found.': 'لم يُعثر على ميكروفون.',
    'The microphone is in use by another app.': 'الميكروفون قيد الاستخدام في تطبيق آخر.',
    'Unknown error': 'خطأ غير معروف',
    'call ended': 'انتهت المكالمة',
    'This browser cannot use the microphone on this page.': 'لا يستطيع هذا المتصفح استخدام الميكروفون في هذه الصفحة.',
    'The server did not return a voice session.': 'لم يُرجع الخادم جلسة صوتية.',
    'Voice error': 'خطأ في الصوت',

    /* values the pages humanize (status, mode, channel, reasons, sources) */
    'Active': 'نشطة',
    'Ended': 'منتهية',
    'Killed': 'أُنهيت',
    'Web': 'الموقع',
    'Sms': 'رسالة نصية',
    'Unknown': 'غير معروف',
    'Regex': 'أنماط',
    'Llm': 'نموذج لغوي',
    'Model': 'نموذج لغوي',
    'Haiku': 'نموذج لغوي',
    'Wind down': 'انسحاب الشخصية',
    'Idle': 'خمول',
    'Timeout': 'انتهاء الوقت',
    'Time limit': 'انتهاء الوقت',
    'Turn limit': 'بلوغ حد الدورات',
    'Kill': 'إنهاء يدوي',
    'Killed by operator': 'أنهاها المشغّل',
    'Reveal': 'الكشف',
    '[conversation started]': '[بدأت المحادثة]',
    '[call connected]': '[اتصلت المكالمة]',

    /* conversation stages (decoy, then drill) */
    'HOOKED': 'التصديق',
    'STALL': 'المماطلة',
    'FISH': 'الاستدراج',
    'CANARY': 'تقديم الطُّعم',
    'WIND_DOWN': 'الانسحاب',
    'PRETEXT': 'الذريعة',
    'PRESSURE': 'الضغط',
    'ASK': 'الطلب',
    'LESSON': 'الدرس',

    /* messages the server can return */
    'Drill refused: this person is not enrolled. Drills need recorded consent.': 'رُفض التمرين: هذا الشخص غير مسجَّل. تتطلب التمارين موافقة مسجّلة.',
    'Voice is not configured for this language on the server.': 'الصوت غير مُعدّ لهذه اللغة على الخادم.',
    'Outbound calls are not set up. Add the ElevenLabs API key and phone number ID.': 'المكالمات الصادرة غير مُعدّة. أضف مفتاح ElevenLabs ومعرّف رقم الهاتف.',
    'The number must be in international format, like +9715XXXXXXXX.': 'يجب أن يكون الرقم بالصيغة الدولية، مثل ‎+9715XXXXXXXX.',
    'This session is not active.': 'هذه الجلسة غير نشطة.',
    'Too many sessions from this address. Try again later.': 'جلسات كثيرة من هذا العنوان. حاول لاحقًا.',
    'Wrong access code': 'رمز الدخول غير صحيح',
    'Unknown conversation': 'محادثة غير معروفة',

    /* evidence tab: the published test run */
    'Intel recall': 'استدعاء المعلومات',
    'Intel precision': 'دقة المعلومات',
    'Scammer time consumed': 'وقت المحتال المُهدَر',
    'Real-data leakage': 'تسرّب بيانات حقيقية',
    'Stop-before-disclosure': 'التوقف قبل الإفصاح',
    'Stop before disclosure': 'التوقف قبل الإفصاح',
    'Wrong would_comply': 'تصنيف «كان سيستجيب» الخاطئ',
    'Requests for a secret that reached the trainee': 'طلبات معلومة سرية وصلت إلى المتدرّب',
    'Drills that ended with a reveal': 'تمارين انتهت بالكشف',
    'Persona breaks': 'الخروج عن الشخصية',
    'First words from the live model': 'أول كلمات من النموذج المباشر',
    'Red-team set': 'مجموعة الهجمات العدائية',
    'details the scammer gave': 'تفصيلًا قدّمها المحتال',
    'turns on average': 'دورات في المتوسط',
    'numbers outside the kit': 'أرقام من خارج المجموعة',
    'replies': 'ردود',
    'where the trainee kept replying': 'استمر فيها المتدرّب بالرد',
    'median (text turns)': 'الوسيط (الدورات النصية)',
    'attacks handled': 'هجمة صُدّت',
    'All': 'الكل',

    /* scenario cards (titles, who they pretend to be, red flags) */
    'Bank security team: suspicious transaction': 'فريق أمن البنك: معاملة مشبوهة',
    'Courier holding a parcel for a small fee': 'شركة شحن تحتجز طردًا مقابل رسوم بسيطة',
    'Refunds office: you are owed money for an overcharge': 'مكتب الاسترداد: لك مبلغ مستحق بسبب رسوم زائدة',
    'Private investment group: guaranteed daily returns': 'مجموعة استثمار خاصة: أرباح يومية مضمونة',
    'Job offer you never applied for: pay the visa fee first': 'عرض عمل لم تتقدّم إليه: ادفع رسوم التأشيرة أولًا',
    'Overseas landlord: pay a deposit before viewing': 'مالك عقار في الخارج: ادفع عربونًا قبل المعاينة',
    'Seized car at half price: pay a deposit to hold it': 'سيارة محجوزة بنصف السعر: ادفع عربونًا لحجزها',
    'Unpaid traffic fine': 'مخالفة مرورية غير مدفوعة',
    'bank security team': 'فريق أمن في بنك',
    'courier company': 'شركة شحن',
    'a consumer protection refunds office': 'مكتب استرداد لحماية المستهلك',
    'a friendly contact running a private investment group': 'معارف ودودون يديرون مجموعة استثمار خاصة',
    'a recruitment agency': 'وكالة توظيف',
    'a private landlord': 'مالك عقار',
    'a private seller of a customs-seized car': 'بائع خاص لسيارة محجوزة جمركيًا',
    'traffic authority': 'جهة مرورية',
    'The bank called you, you did not call the bank': 'البنك هو من اتصل بك، لا أنت من اتصل بالبنك',
    'Pressure to act within minutes': 'الضغط للتصرف خلال دقائق',
    'A request for a one-time code': 'طلب رمز التحقق لمرة واحدة',
    'You were not expecting a parcel': 'لم تكن تنتظر أي طرد',
    'A tiny fee used to collect full card details': 'رسوم زهيدة لجمع بيانات البطاقة كاملة',
    'A return-to-sender deadline tonight': 'مهلة لإعادة الطرد تنتهي الليلة',
    'A refund you never asked for': 'مبلغ مسترد لم تطلبه',
    'A deadline to claim it today': 'مهلة لاستلامه تنتهي اليوم',
    'A request for your card details to receive money': 'طلب بيانات بطاقتك لتستلم مالًا',
    'Guaranteed daily returns': 'أرباح يومية مضمونة',
    'A deadline to join today': 'مهلة للانضمام تنتهي اليوم',
    'Payment only in crypto': 'الدفع بالعملات المشفّرة فقط',
    'A job offer for a role you never applied for': 'عرض عمل لوظيفة لم تتقدّم إليها',
    'A fee must be paid before you get a contract': 'رسوم يجب دفعها قبل استلام العقد',
    'Pressure to decide today or lose the job': 'الضغط لاتخاذ القرار اليوم وإلا ضاعت الوظيفة',
    'The landlord is abroad and cannot show the flat': 'المالك خارج الدولة ولا يستطيع عرض الشقة',
    'Rent far below similar flats': 'إيجار أقل بكثير من الشقق المماثلة',
    'Deposit demanded before any viewing': 'طلب عربون قبل أي معاينة',
    'Price far below market value': 'سعر أقل بكثير من سعر السوق',
    'Pressure from other buyers today': 'الضغط بوجود مشترين آخرين اليوم',
    'The message did not come from an official channel': 'الرسالة لم تصل من قناة رسمية',
    'A threat with a same-day deadline': 'تهديد بمهلة تنتهي في اليوم نفسه',
    'A request for card details and a one-time code': 'طلب بيانات البطاقة ورمز التحقق لمرة واحدة',

    /* personas */
    'Retired Emirati grandfather in Al Ain, slow with phones, his son Khalid usually helps him with the bank':
      'جدّ إماراتي متقاعد في العين، بطيء في استخدام الهاتف، ويساعده ابنه خالد عادةً في شؤون البنك',
    'Accountant, arrived in Abu Dhabi four months ago, worried about anything that could affect his visa':
      'محاسب وصل إلى أبوظبي قبل أربعة أشهر، ويقلقه كل ما قد يؤثر في تأشيرته',
    'Marketing coordinator, always between meetings, handles everything from her phone':
      'منسّقة تسويق، تنتقل دائمًا بين الاجتماعات، وتنجز كل شيء من هاتفها'
  };

  /* Only as a placeholder: the same word can be a group name someone typed. */
  var AR_ATTR_ONLY = { 'Pilot': 'تجريبي' };

  /* Persona names are translated only where they name a persona, never where a person typed a name. */
  var NAMES = { 'Rajesh': 'راجيش', 'Sara': 'سارة', 'Abu Khalid': 'أبو خالد' };
  var NAME_PLACES = '#personas, .phone-head, #sessions-body, #detail-title, .sample, .msg-meta, .transcript-hint';

  var LANGS = { ar: 'العربية', en: 'الإنجليزية' };
  var MONTHS = { Jan: 'يناير', Feb: 'فبراير', Mar: 'مارس', Apr: 'أبريل', May: 'مايو', Jun: 'يونيو',
                 Jul: 'يوليو', Aug: 'أغسطس', Sep: 'سبتمبر', Oct: 'أكتوبر', Nov: 'نوفمبر', Dec: 'ديسمبر' };
  var SP = '[\\s\\u00a0\\u202f]';
  function ampm(x) { return /^a/i.test(x) ? 'ص' : 'م'; }
  function plural(n, one, many) { return Number(n) === 1 ? one : many; }

  /* Translates a piece of text if it is known; otherwise returns it unchanged. */
  function tr(text, scope) {
    var out = lookup(text, scope);
    return out == null ? text : out;
  }
  function trCap(text) {                                     /* "would comply" -> "Would comply" -> Arabic */
    var t = String(text);
    return tr(t.charAt(0).toUpperCase() + t.slice(1));
  }
  function name(text, scope) { return Object.prototype.hasOwnProperty.call(NAMES, text) ? NAMES[text] : tr(text, scope); }

  /* "Could not load sessions: <server message>" and friends: Arabic prefix, translated remainder. */
  var PREFIXES = [
    ['Could not load personas: ', 'تعذّر تحميل الشخصيات: '],
    ['Could not load scenarios: ', 'تعذّر تحميل السيناريوهات: '],
    ['Could not enrol: ', 'تعذّر التسجيل: '],
    ['Could not start the drill: ', 'تعذّر بدء التمرين: '],
    ['Could not stop the drill: ', 'تعذّر إيقاف التمرين: '],
    ['Could not end the session: ', 'تعذّر إنهاء الجلسة: '],
    ['Could not reach the server: ', 'تعذّر الوصول إلى الخادم: '],
    ['Could not send: ', 'تعذّر الإرسال: '],
    ['Could not load call settings: ', 'تعذّر تحميل إعدادات المكالمة: '],
    ['Could not place the call: ', 'تعذّر إجراء المكالمة: '],
    ['Could not load the overview: ', 'تعذّر تحميل النظرة العامة: '],
    ['Could not load sessions: ', 'تعذّر تحميل الجلسات: '],
    ['Could not load this session: ', 'تعذّر تحميل هذه الجلسة: '],
    ['Could not load campaigns: ', 'تعذّر تحميل الحملات: '],
    ['Could not load drill results: ', 'تعذّر تحميل نتائج التمارين: '],
    ['Could not load invites: ', 'تعذّر تحميل الدعوات: '],
    ['Could not create the invite: ', 'تعذّر إنشاء الدعوة: '],
    ['Could not load cases: ', 'تعذّر تحميل القضايا: '],
    ['Could not load test results: ', 'تعذّر تحميل نتائج الاختبار: '],
    ['Message not sent: ', 'لم تُرسَل الرسالة: '],
    ['Voice problem: ', 'مشكلة في الصوت: '],
    ['Rating not sent: ', 'لم يُرسَل التقييم: '],
    ['Session ended: ', 'انتهت الجلسة: '],
    ['Guardrail: ', 'الحماية: '],
    ['Drill outcome: ', 'نتيجة التمرين: '],
    ['Updated ', 'آخر تحديث '],
    ['Target ', 'الهدف: '],
    ['Drill — ', 'تمرين — ']
  ];

  /* Text the pages assemble from parts. Each rule: [pattern, function(match, scope) -> Arabic]. */
  var RULES = [
    [new RegExp('^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\\d{1,2}), (\\d{1,2}:\\d{2})' + SP + '?(AM|PM|am|pm)$'),
      function (m) { return m[2] + ' ' + MONTHS[m[1]] + '، ' + m[3] + ' ' + ampm(m[4]); }],
    [new RegExp('^(\\d{1,2}:\\d{2})' + SP + '?(AM|PM|am|pm)$'), function (m) { return m[1] + ' ' + ampm(m[2]); }],
    [/^From (.+)$/, function (m, s) { return 'من ' + name(m[1], s); }],
    [/^Open session: (.+), ((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [\s\S]+)$/,
      function (m) { return 'فتح الجلسة: ' + (NAMES[m[1]] || tr(m[1])) + '، ' + tr(m[2]); }],
    [/^Open session: (.+)$/, function (m) { return 'فتح الجلسة: ' + (NAMES[m[1]] || tr(m[1])); }],
    [/^Stage: ([A-Z_]+)(?:\. ([\s\S]*))?$/, function (m) { return 'المرحلة: ' + tr(m[1]) + (m[2] ? '. ' + m[2] : ''); }],
    [/^Calling (.+)\. Speak when the call connects\.$/, function (m, s) { return 'جارٍ الاتصال بـ' + name(m[1], s) + '. تحدّث عندما يتصل الخط.'; }],
    [/^The call did not start\. You can write to (.+) instead\.$/, function (m, s) { return 'لم تبدأ المكالمة. يمكنك مراسلة ' + name(m[1], s) + ' كتابيًا بدلًا من ذلك.'; }],
    [/^Call could not start: (.*?) ?You can carry on by text\.$/, function (m) { return 'تعذّر بدء المكالمة: ' + tr(m[1].trim()) + ' يمكنك المتابعة كتابيًا.'; }],
    [/^(.+) is there\. You write first\.$/, function (m, s) { return name(m[1], s) + ' بانتظارك. ابدأ أنت بالكتابة.'; }],
    [/^Calling (\+?[\d ]+) now\. The phone should ring shortly\.$/, function (m) { return 'جارٍ الاتصال بالرقم ‎' + m[1] + ' الآن. سيرنّ الهاتف قريبًا.'; }],
    [/^Age (\d+)(?:, (\w+))?$/, function (m) { return 'العمر ' + m[1] + (m[2] ? '، ' + (LANGS[m[2]] || m[2]) : ''); }],
    [/^Difficulty: (\S+?)(?:, (\w+))?$/, function (m) { return 'الصعوبة: ' + m[1] + (m[2] ? '، ' + (LANGS[m[2]] || m[2]) : ''); }],
    [/^Pretends to be (.+)$/, function (m) { return 'ينتحل صفة ' + tr(m[1]); }],
    [/^Enrolled as (.+)\. Pick a scenario and how it reaches you\.$/, function (m) { return 'سُجّلت باسم ' + m[1].replace(/, /g, '، ') + '. اختر سيناريو وطريقة وصوله إليك.'; }],
    [/^(\d+) more scenarios are waiting for approval and cannot be used yet\.$/, function (m) { return 'هناك ' + m[1] + ' سيناريوهات أخرى بانتظار الاعتماد ولا يمكن استخدامها بعد.'; }],
    [/^The request failed before the consent check \((.+?)\): (.*)$/, function (m) { return 'فشل الطلب قبل فحص الموافقة (' + tr(m[1]) + '): ' + tr(m[2]); }],
    [/^Emails are sent from (.+)\. Results show on the dashboard\.$/, function (m) { return 'تُرسَل الرسائل من ' + tr(m[1]) + '. تظهر النتائج في لوحة المتابعة.'; }],
    [/^Sending (\d+) emails?(?: \((\d+) skipped\))?\. Who clicks shows on the dashboard\.$/,
      function (m) { return 'جارٍ إرسال ' + m[1] + ' ' + plural(m[1], 'رسالة', 'رسائل') + (m[2] ? ' (تخطّي ' + m[2] + ')' : '') + '. يظهر مَن ينقر الرابط في لوحة المتابعة.'; }],
    [/^The server returned an error \((\d+)\)\.$/, function (m) { return 'أعاد الخادم خطأً (' + m[1] + ').'; }],
    [/^(\d+) of (\d+)$/, function (m) { return m[1] + ' من ' + m[2]; }],
    [/^(\d+) at risk \((\d+)%\)$/, function (m) { return m[1] + ' معرّضون للخطر (' + m[2] + '%)'; }],
    [/^(\d+) clicked \((\d+)%\)$/, function (m) { return 'نقر ' + m[1] + ' (' + m[2] + '%)'; }],
    [/^(\d+) details captured$/, function (m) { return 'تفاصيل ملتقطة: ' + m[1]; }],
    [/^Groups below (\d+) people are hidden, so no one is singled out\.$/, function (m) { return 'تُخفى المجموعات التي يقل عدد أفرادها عن ' + m[1] + '، فلا يُميَّز أحد.'; }],
    [/^Groups below the minimum size of (\d+) are not listed, so no one can be singled out\.$/, function (m) { return 'لا تُعرض المجموعات التي يقل حجمها عن ' + m[1] + '، فلا يمكن تمييز أحد.'; }],
    [/^Started (.+?)(?:\. Channel: (.+?))?(?:\. Turns: (\d+))?(?:\. Director note: ([\s\S]*))?$/,
      function (m) {
        var out = ['البدء ' + tr(m[1])];
        if (m[2]) out.push('القناة: ' + tr(m[2]));
        if (m[3]) out.push('الدورات: ' + m[3]);
        if (m[4] != null) out.push('ملاحظة الموجِّه: ' + m[4]);
        return out.join('. ');
      }],
    [/^Channel: (.+)$/, function (m) { return 'القناة: ' + tr(m[1]); }],
    [/^Turns: (\d+)$/, function (m) { return 'الدورات: ' + m[1]; }],
    [/^after (\d+) turns?$/, function (m) { return 'بعد ' + m[1] + ' ' + plural(m[1], 'دورة', 'دورات'); }],
    [/^Message from (.+)$/, function (m, s) { return 'رسالة من ' + trCap(name(m[1], s)); }],
    [/^Intel captured: (\S+) ([\s\S]*)$/, function (m) { return 'معلومة ملتقطة: ' + tr(m[1]) + ' ' + m[2]; }],
    [/^Source: (.+?)(?:, Confidence: (.+))?$/, function (m) { return 'المصدر: ' + tr(m[1]) + (m[2] ? '، الثقة: ' + m[2] : ''); }],
    [/^Confidence: (.+)$/, function (m) { return 'الثقة: ' + m[1]; }],
    [/^Session: (.+)\. Linked to (\d+) intel items?\.$/, function (m) { return 'الجلسة: ' + m[1] + '. مرتبطة بـ' + m[2] + ' ' + plural(m[2], 'معلومة', 'معلومات') + '.'; }],
    [/^([A-Za-z ]+): (.+)\. Seen in (\d+) sessions?\.$/, function (m) { return tr(m[1]) + ': ' + m[2] + '. ظهرت في ' + m[3] + ' ' + plural(m[3], 'جلسة', 'جلسات') + '.'; }],
    [/^(\d+) minutes$/, function (m) { return m[1] + ' دقيقة'; }],
    [/^(\d+) hours$/, function (m) { return m[1] + ' ساعة'; }],
    [/^(\d+) days$/, function (m) { return m[1] + ' يوم'; }],
    [/^(.+) \(Arabic\)$/, function (m) { return tr(m[1]) + ' (بالعربية)'; }],
    [/^(784-[\d-]+)\s+✓ verified$/, function (m) { return m[1] + ' ✓ موثّقة'; }],
    [/^✓ verified$/, function () { return '✓ موثّقة'; }],
    [/^✓ Case details emailed to (.+)$/, function (m) { return '✓ أُرسلت تفاصيل القضية إلى ' + tr(m[1]); }],
    [/^Latest test run(?:, ([\d-]+))?\. (\d+) of (\d+) targets met\.$/,
      function (m) { return 'أحدث تشغيل للاختبار' + (m[1] ? '، ' + m[1] : '') + '. تحقق ' + m[2] + ' من ' + m[3] + ' أهداف.'; }],
    [/^(\d+) of (\d+) (details the scammer gave)$/, function (m) { return m[1] + ' من ' + m[2] + ' ' + tr(m[3]); }],
    [/^(\d+) of (\d+) drills where a code was given$/, function (m) { return m[1] + ' من ' + m[2] + ' تمرينًا قُدّم فيها رمز'; }],
    [/^(\d+) of (\d+) sceptical trainees$/, function (m) { return m[1] + ' من ' + m[2] + ' متدرّبًا متشككًا'; }],
    [/^per 100 conversations \((\d+) in (\d+)\)$/, function (m) { return 'لكل 100 محادثة (' + m[1] + ' من ' + m[2] + ')'; }],
    [/^([\d.]+)% or higher$/, function (m) { return m[1] + '% أو أعلى'; }],
    [/^(\d+) or more$/, function (m) { return m[1] + ' أو أكثر'; }],
    [/^Under (.+)$/, function (m) { return 'أقل من ' + tr(m[1]); }],
    [/^([\d.]+) s$/, function (m) { return m[1] + ' ث'; }]
  ];

  function lookup(raw, scope) {
    var text = String(raw).replace(/\s+/g, ' ').trim();
    if (!text || !/[A-Za-z]/.test(text)) return null;
    if (Object.prototype.hasOwnProperty.call(AR, text)) return AR[text];
    if (scope && Object.prototype.hasOwnProperty.call(NAMES, text) && scope.closest && scope.closest(NAME_PLACES)) return NAMES[text];
    for (var i = 0; i < PREFIXES.length; i++) {
      var p = PREFIXES[i][0];
      if (text.indexOf(p) === 0 && text.length > p.length) {
        var rest = text.slice(p.length);
        var inner = PREFIXES[i][1] === 'تمرين — ' ? trCap(rest) : tr(rest, scope);
        return PREFIXES[i][1] + inner;
      }
    }
    for (var j = 0; j < RULES.length; j++) {
      var m = RULES[j][0].exec(text);
      if (m) return RULES[j][1](m, scope);
    }
    return null;
  }

  /* ------------------------------------------------------------ applying it to the page */
  /* Inside these, nothing is translated: the conversation, captured details, what people typed,
     and the drill's own lesson (which is in the language the drill was run in). */
  var KEEP = '.lang-toggle, script, style, code, textarea, .msg--agent .bubble, .msg--counterpart .bubble, ' +
             '.intel-value, .intel-quote, .stage-note, #lesson-head, #lesson-points, #flags, #report-to, #reveal-text';
  var ALWAYS = '.sample';                       /* the landing page's sample chat is illustration, not data */
  var ATTRS = ['placeholder', 'aria-label', 'title'];

  var textOriginal = new WeakMap();             /* text node -> its English */
  var textShown = new WeakMap();                /* text node -> the Arabic we put there */
  var attrOriginal = new WeakMap();             /* element -> { attr: English } */
  var touched = new Set();
  var titleOriginal = null;

  function kept(el) {
    if (!el || !el.closest) return false;
    return !!el.closest(KEEP) && !el.closest(ALWAYS);
  }

  function translateText(node) {
    var value = node.nodeValue;
    if (!value || !/[A-Za-z]/.test(value)) return;
    if (textShown.get(node) === value) return;               /* our own text */
    var parent = node.parentElement;
    if (!parent || kept(parent)) return;
    var ar = lookup(value, parent);
    if (ar == null) return;
    var lead = value.match(/^\s*/)[0], trail = value.match(/\s*$/)[0];
    var shown = lead + ar + trail;
    textOriginal.set(node, value);
    textShown.set(node, shown);
    touched.add(node);
    node.nodeValue = shown;
  }

  function translateAttrs(el) {
    if (el.closest && el.closest('.lang-toggle')) return;     /* placeholders and labels of inputs are interface */
    ATTRS.forEach(function (attr) {
      if (!el.hasAttribute(attr)) return;
      var value = el.getAttribute(attr);
      var store = attrOriginal.get(el) || {};
      if (store[attr] && store[attr].shown === value) return;
      var ar = Object.prototype.hasOwnProperty.call(AR_ATTR_ONLY, value) ? AR_ATTR_ONLY[value] : lookup(value, el);
      if (ar == null) return;
      store[attr] = { en: value, shown: ar };
      attrOriginal.set(el, store);
      touched.add(el);
      el.setAttribute(attr, ar);
    });
  }

  /* The drill's lesson stays in the drill's own language. In the Arabic layout each of its lines takes the
     direction of its own text (dir="auto"), so an English lesson still reads left to right. */
  var OWN_DIRECTION = '#reveal-text, #lesson-head, #lesson-points > li, #flags > li, #report-to';
  var directed = new Set();

  function directContent(root) {
    var list = [];
    if (root.matches && root.matches(OWN_DIRECTION)) list.push(root);
    if (root.querySelectorAll) list = list.concat(Array.prototype.slice.call(root.querySelectorAll(OWN_DIRECTION)));
    if (root.parentElement && root.parentElement.closest) {
      var host = root.parentElement.closest(OWN_DIRECTION);
      if (host) list.push(host);
    }
    list.forEach(function (el) {
      if (!el.hasAttribute('dir')) { el.setAttribute('dir', 'auto'); directed.add(el); }
    });
  }

  function undirectContent() {
    directed.forEach(function (el) { if (el.getAttribute('dir') === 'auto') el.removeAttribute('dir'); });
    directed.clear();
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { translateText(root); if (root.parentElement) directContent(root.parentElement); return; }
    if (root.nodeType !== 1) return;
    directContent(root);
    translateAttrs(root);
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var node;
    var nodes = [];
    while ((node = walker.nextNode())) nodes.push(node);
    nodes.forEach(translateText);
    root.querySelectorAll('[placeholder], [aria-label], [title]').forEach(translateAttrs);
  }

  function translateTitle() {
    var ar = lookup(document.title);
    if (ar != null) { titleOriginal = document.title; document.title = ar; }
  }

  function restoreAll() {
    touched.forEach(function (item) {
      if (item.nodeType === 3) {
        if (textShown.get(item) === item.nodeValue) item.nodeValue = textOriginal.get(item);
        textShown.delete(item);
      } else {
        var store = attrOriginal.get(item) || {};
        Object.keys(store).forEach(function (attr) {
          if (item.getAttribute(attr) === store[attr].shown) item.setAttribute(attr, store[attr].en);
        });
        attrOriginal.delete(item);
      }
    });
    touched.clear();
    undirectContent();
    if (titleOriginal != null) { document.title = titleOriginal; titleOriginal = null; }
  }

  var observer = new MutationObserver(function (records) {
    if (lang !== 'ar') return;
    records.forEach(function (r) {
      if (r.type === 'characterData') translateText(r.target);
      else if (r.type === 'attributes') {
        if (r.attributeName === 'dir') directContent(r.target);
        else translateAttrs(r.target);
      }
      else r.addedNodes.forEach(walk);
    });
  });

  /* ------------------------------------------------------------ the switch */
  var button = null;

  function labelButton() {
    if (!button) return;
    button.textContent = lang === 'ar' ? 'English' : 'العربية';
    button.setAttribute('lang', lang === 'ar' ? 'en' : 'ar');
    button.setAttribute('aria-label', lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية');
  }

  function setLanguage(next) {
    lang = next;
    try { localStorage.setItem(KEY, lang); } catch (e) { /* storage blocked */ }
    applyDirection();
    if (lang === 'ar') { walk(document.body); translateTitle(); }
    else restoreAll();
    labelButton();
  }

  function start() {
    var status = document.getElementById('status');
    var bar = document.querySelector('.topbar');
    if (bar) {
      button = document.createElement('button');
      button.type = 'button';
      button.className = 'lang-toggle';
      button.addEventListener('click', function () { setLanguage(lang === 'ar' ? 'en' : 'ar'); });
      bar.insertBefore(button, status && status.parentNode === bar ? status : null);
      labelButton();
    }
    observer.observe(document.body, { childList: true, subtree: true, characterData: true,
                                      attributes: true, attributeFilter: ATTRS.concat(['dir']) });
    if (lang === 'ar') { walk(document.body); translateTitle(); }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
