"""One-off script to generate fetcher_seeds.py — run from repo root."""
from pathlib import Path

# fmt: off
FLASHCARD_PAIRS = [
    # Transport (25)
    ("la estación de metro", "the metro station"),
    ("el andén", "the platform"),
    ("¿A qué hora sale el próximo metro?", "What time does the next metro leave?"),
    ("un billete sencillo", "a single ticket"),
    ("un abono de transporte", "a transport pass"),
    ("la línea de metro", "the metro line"),
    ("el mapa del metro", "the metro map"),
    ("la parada de autobús", "the bus stop"),
    ("el billete de bus", "the bus ticket"),
    ("la tarjeta T-usual", "the T-usual card"),
    ("validar el billete", "to validate the ticket"),
    ("el transbordo", "the transfer"),
    ("la estación de Rodalies", "the Rodalies station"),
    ("el tren de cercanías", "the commuter train"),
    ("¿Dónde está la salida?", "Where is the exit?"),
    ("el ascensor", "the elevator"),
    ("las escaleras mecánicas", "the escalators"),
    ("el retraso del tren", "the train delay"),
    ("la huelga de transporte", "the transport strike"),
    ("el aeropuerto de El Prat", "El Prat airport"),
    ("el aerobús", "the airport bus"),
    ("un taxi oficial", "an official taxi"),
    ("la parada de taxi", "the taxi rank"),
    ("el atasco de tráfico", "the traffic jam"),
    ("la zona azul", "the blue parking zone"),
    # Food & restaurants (25)
    ("el menú del día", "the set lunch menu"),
    ("la cuenta, por favor", "the bill, please"),
    ("¿Cuánto cuesta?", "How much does it cost?"),
    ("una mesa para dos", "a table for two"),
    ("sin gluten", "gluten-free"),
    ("alergia a los frutos secos", "nut allergy"),
    ("la propina", "the tip"),
    ("el camarero", "the waiter"),
    ("la carta de vinos", "the wine list"),
    ("un café con leche", "a coffee with milk"),
    ("una cerveza pequeña", "a small beer"),
    ("agua sin gas", "still water"),
    ("agua con gas", "sparkling water"),
    ("para llevar", "to take away"),
    ("la terraza", "the terrace"),
    ("el desayuno", "breakfast"),
    ("la comida", "lunch"),
    ("la cena", "dinner"),
    ("el postre", "dessert"),
    ("está delicioso", "it's delicious"),
    ("sin cebolla", "without onion"),
    ("bien hecho", "well done"),
    ("poco hecho", "rare"),
    ("la reserva", "the reservation"),
    ("¿Tienen menú en inglés?", "Do you have a menu in English?"),
    # Markets (15)
    ("el mercado municipal", "the municipal market"),
    ("La Boqueria", "La Boqueria market"),
    ("un kilo de tomates", "a kilo of tomatoes"),
    ("medio kilo", "half a kilo"),
    ("¿Cuánto pesa?", "How much does it weigh?"),
    ("la bolsa reutilizable", "the reusable bag"),
    ("el pescadero", "the fishmonger"),
    ("la frutería", "the greengrocer"),
    ("fresco del día", "fresh today"),
    ("la oferta", "the special offer"),
    ("el precio por kilo", "the price per kilo"),
    ("¿Puedo probarlo?", "Can I try it?"),
    ("la cola en la caja", "the queue at the checkout"),
    ("pagar en efectivo", "to pay in cash"),
    ("pagar con tarjeta", "to pay by card"),
    # Healthcare (15)
    ("el centro de salud", "the health center"),
    ("la tarjeta sanitaria", "the health card"),
    ("pedir cita médica", "to request a doctor's appointment"),
    ("la farmacia", "the pharmacy"),
    ("la receta médica", "the prescription"),
    ("¿Dónde está la urgencia?", "Where is the emergency room?"),
    ("me duele la cabeza", "my head hurts"),
    ("tengo fiebre", "I have a fever"),
    ("la alergia", "the allergy"),
    ("el seguro médico", "health insurance"),
    ("la mutua", "the private health insurer"),
    ("el médico de cabecera", "the GP"),
    ("la enfermera", "the nurse"),
    ("las pastillas", "the pills"),
    ("la baja médica", "sick leave"),
    # Housing (15)
    ("el piso compartido", "the shared flat"),
    ("el contrato de alquiler", "the rental contract"),
    ("la fianza", "the deposit"),
    ("el casero", "the landlord"),
    ("la comunidad de vecinos", "the residents' association"),
    ("las facturas", "the bills"),
    ("el recibo del alquiler", "the rent receipt"),
    ("la avería", "the breakdown / fault"),
    ("el fontanero", "the plumber"),
    ("la calefacción", "the heating"),
    ("el aire acondicionado", "the air conditioning"),
    ("las obras en el edificio", "building works"),
    ("el piso amueblado", "the furnished flat"),
    ("buscar piso", "to look for a flat"),
    ("la agencia inmobiliaria", "the estate agency"),
    # University (15)
    ("la universidad", "the university"),
    ("la matrícula", "enrollment"),
    ("el horario de clases", "the class schedule"),
    ("el campus", "the campus"),
    ("la biblioteca", "the library"),
    ("el profesor", "the professor"),
    ("la asignatura", "the subject / course"),
    ("el examen final", "the final exam"),
    ("la nota", "the grade"),
    ("el trabajo en grupo", "group work"),
    ("la beca", "the scholarship"),
    ("el intercambio", "the exchange program"),
    ("la secretaría académica", "the academic office"),
    ("el carnet de estudiante", "the student ID"),
    ("la tutoría", "the tutorial session"),
    # Directions (15)
    ("¿Dónde está el baño?", "Where is the bathroom?"),
    ("a la derecha", "to the right"),
    ("a la izquierda", "to the left"),
    ("todo recto", "straight ahead"),
    ("la esquina", "the corner"),
    ("la plaza", "the square"),
    ("el semáforo", "the traffic light"),
    ("el paso de peatones", "the crosswalk"),
    ("¿Está lejos?", "Is it far?"),
    ("¿Está cerca?", "Is it near?"),
    ("a cinco minutos a pie", "five minutes on foot"),
    ("el mapa", "the map"),
    ("perderse", "to get lost"),
    ("¿Cómo llego a...?", "How do I get to...?"),
    ("la dirección", "the address / direction"),
    # Social phrases (15)
    ("buenos días", "good morning"),
    ("buenas tardes", "good afternoon"),
    ("buenas noches", "good evening"),
    ("muchas gracias", "thank you very much"),
    ("de nada", "you're welcome"),
    ("perdón", "sorry / excuse me"),
    ("encantado de conocerte", "nice to meet you"),
    ("¿Qué tal?", "How's it going?"),
    ("hasta luego", "see you later"),
    ("nos vemos", "see you"),
    ("¿De dónde eres?", "Where are you from?"),
    ("soy estudiante", "I'm a student"),
    ("hablo un poco de español", "I speak a little Spanish"),
    ("¿Puedes repetir?", "Can you repeat that?"),
    ("más despacio, por favor", "more slowly, please"),
    # Weather (10)
    ("hace sol", "it's sunny"),
    ("está lloviendo", "it's raining"),
    ("hace frío", "it's cold"),
    ("hace calor", "it's hot"),
    ("el pronóstico del tiempo", "the weather forecast"),
    ("la tormenta", "the storm"),
    ("el viento", "the wind"),
    ("la humedad", "the humidity"),
    ("¿Qué tiempo hace?", "What's the weather like?"),
    ("la ola de calor", "the heat wave"),
    # Bureaucracy (15)
    ("el empadronamiento", "municipal registration"),
    ("el NIE", "foreigner ID number"),
    ("la residencia", "residence permit"),
    ("la cita previa", "the prior appointment"),
    ("la oficina de extranjería", "the immigration office"),
    ("el certificado", "the certificate"),
    ("la documentación", "the paperwork"),
    ("el formulario", "the form"),
    ("firmar el contrato", "to sign the contract"),
    ("la copia compulsada", "the certified copy"),
    ("tramitar el visado", "to process the visa"),
    ("la cola en la oficina", "the queue at the office"),
    ("el número de turno", "the queue number"),
    ("la tasa administrativa", "the administrative fee"),
    ("presentar la solicitud", "to submit the application"),
    # Catalan signage (10)
    ("sortida", "exit (Catalan)"),
    ("entrada", "entrance (Catalan)"),
    ("obert", "open (Catalan)"),
    ("tancat", "closed (Catalan)"),
    ("parada", "stop (Catalan)"),
    ("adéu", "goodbye (Catalan)"),
    ("si us plau", "please (Catalan)"),
    ("gràcies", "thanks (Catalan)"),
    ("dilluns", "Monday (Catalan)"),
    ("dissabte", "Saturday (Catalan)"),
    # Verbs B1/B2 (20)
    ("reservar una mesa", "to book a table"),
    ("tramitar el papeleo", "to handle the paperwork"),
    ("alquilar un piso", "to rent a flat"),
    ("compartir gastos", "to share expenses"),
    ("apuntarse al gimnasio", "to sign up at the gym"),
    ("echar de menos", "to miss (someone)"),
    ("acostumbrarse a", "to get used to"),
    ("quedarse sin batería", "to run out of battery"),
    ("recargar el móvil", "to charge the phone"),
    ("perder el WiFi", "to lose the WiFi"),
    ("solicitar información", "to request information"),
    ("devolver el libro", "to return the book"),
    ("aprobar el examen", "to pass the exam"),
    ("suspender el examen", "to fail the exam"),
    ("entregar el trabajo", "to hand in the assignment"),
    ("hacer la colada", "to do the laundry"),
    ("fregar los platos", "to wash the dishes"),
    ("sacar la basura", "to take out the trash"),
    ("regatear el precio", "to bargain the price"),
    ("cambiar de opinión", "to change one's mind"),
    # Extra Barcelona (10)
    ("la playa de la Barceloneta", "Barceloneta beach"),
    ("el Barrio Gótico", "the Gothic Quarter"),
    ("la Sagrada Familia", "the Sagrada Familia"),
    ("el Park Güell", "Park Güell"),
    ("la Rambla", "the Rambla"),
    ("el castell de Montjuïc", "Montjuïc castle"),
    ("el festival de La Mercè", "La Mercè festival"),
    ("Sant Jordi", "Saint George's Day"),
    ("la Diada", "Catalan National Day"),
    ("el castellano y el catalán", "Spanish and Catalan"),
]

DAILY_SENTENCES_ES = [
    "¿Dónde está la estación de metro más cercana a la Plaça de Catalunya?",
    "Necesito comprar un abono de transporte para estudiar en Barcelona un semestre.",
    "¿A qué hora abre la biblioteca de la universidad los sábados?",
    "Quiero reservar una mesa en un restaurante cerca de la playa para el viernes.",
    "¿Cuánto cuesta el menú del día con bebida incluida?",
    "Me he perdido en el Barrio Gótico; ¿puede indicarme cómo llegar al metro?",
    "Tengo cita en el CAP mañana por la mañana para renovar la tarjeta sanitaria.",
    "¿Puedo pagar el alquiler del piso por transferencia bancaria?",
    "Busco un piso compartido cerca del campus con internet incluido.",
    "¿Qué documentos necesito para el empadronamiento en el ayuntamiento?",
    "El tren de Rodalies lleva veinte minutos de retraso por una incidencia.",
    "¿Hay alguna farmacia abierta ahora cerca de la Sagrada Familia?",
    "Quiero apuntarme a clases de catalán para entender las señales del metro.",
    "¿Cuál es la mejor línea de metro para ir del aeropuerto al centro?",
    "Hoy hace mucho calor; prefiero estudiar por la tarde en la biblioteca.",
    "¿Dónde puedo validar mi billete antes de subir al autobús?",
    "Necesito cambiar mi cita en la oficina de extranjería por un conflicto de horario.",
    "¿Este mercado municipal abre los domingos por la mañana?",
    "Voy a entregar el trabajo de la universidad antes del plazo de las cinco.",
    "¿Puedo llevar la maleta grande en el ascensor del metro?",
    "Quiero abrir una cuenta bancaria en España siendo estudiante extranjero.",
    "¿A qué hora empieza el concierto de La Mercè en el parque?",
    "El casero me ha pedido la fianza y el primer mes de alquiler por adelantado.",
    "¿Hay WiFi gratuito en la sala de estudio del campus?",
    "Necesito una copia del contrato de alquiler para tramitar la residencia.",
    "¿Dónde está la parada del aerobús en la terminal T1?",
    "Prefiero comprar fruta fresca en el mercado que en el supermercado.",
    "¿Cuánto tarda el visado de estudiante en estar listo?",
    "Me duele la garganta y quiero pedir cita con el médico de cabecera.",
    "¿Se puede pagar con tarjeta en la feria de Sant Jordi?",
    "Voy a tomar el cercanías hasta Sants y luego cambiar al metro.",
    "¿Qué barrio recomiendas para vivir si estudio en la Universidad de Barcelona?",
]

DAILY_PHRASES_ES = [
    "buenos días",
    "muchas gracias",
    "perdón, ¿me ayuda?",
    "un café con leche, por favor",
    "la cuenta, por favor",
    "¿Cuánto cuesta?",
    "no entiendo",
    "¿Puede repetir?",
    "más despacio, por favor",
    "¿Dónde está la salida?",
    "un billete de metro",
    "necesito ayuda",
    "estoy perdido",
    "tengo una reserva",
    "sin gluten, por favor",
    "para llevar",
    "¿Aceptan tarjeta?",
    "¿Hay WiFi?",
    "soy estudiante de intercambio",
    "hablo un poco de catalán",
    "hasta mañana",
    "nos vemos en clase",
    "qué bien",
    "qué pena",
    "en serio",
    "de acuerdo",
    "no pasa nada",
    "¡cuidado!",
    "¡felicidades!",
    "buen viaje",
    "buen provecho",
    "¡salud!",
]

READER_PASSAGES = [
    {
        "id": "metro-bus",
        "lang": "es",
        "title": "Moverse en Barcelona: metro y bus",
        "body": (
            "Barcelona tiene una red de metro amplia y fácil de usar si conoces algunas reglas básicas. "
            "Antes de entrar, compra un billete o recarga tu tarjeta T-usual en las máquinas de la estación. "
            "Recuerda validar el billete en los lectores amarillos; si no lo haces, puedes recibir una multa. "
            "En hora punta los vagones van muy llenos, especialmente en las líneas que cruzan el centro. "
            "Los autobuses complementan el metro y llegan a barrios donde no hay estación cercana. "
            "Consulta la aplicación oficial para ver retrasos y obras. Si vienes del aeropuerto, el aerobús "
            "es cómodo aunque cuesta más que el metro. Pregunta siempre si hay transbordo y cuántas zonas "
            "cubre tu título de transporte. Con un poco de práctica, moverte por la ciudad se vuelve automático."
        ),
        "en": (
            "Barcelona has a large metro network that is easy to use if you know a few basic rules. "
            "Before entering, buy a ticket or reload your T-usual card at the station machines. "
            "Remember to validate your ticket at the yellow readers; if you do not, you may receive a fine. "
            "At rush hour the carriages are very crowded, especially on lines that cross the center. "
            "Buses complement the metro and reach neighborhoods where there is no nearby station. "
            "Check the official app to see delays and works. If you come from the airport, the Aerobús "
            "is convenient although it costs more than the metro. Always ask if there is a transfer and how many zones "
            "your transport pass covers. With a little practice, getting around the city becomes automatic."
        ),
    },
    {
        "id": "boqueria",
        "lang": "es",
        "title": "La Boqueria y los mercados de la ciudad",
        "body": (
            "La Boqueria es uno de los mercados más famosos de Barcelona y un lugar perfecto para practicar español "
            "con los vendedores. Llega temprano si quieres evitar multitudes y encontrar pescado y fruta muy frescos. "
            "Muchos puestos muestran precios por kilo; observa la balanza y pregunta si no entiendes el peso. "
            "Es normal saludar con un «buenos días» antes de pedir. En otros barrios encontrarás mercados municipales "
            "más tranquilos y a menudo más baratos. Lleva una bolsa reutilizable y efectivo por si la tarjeta falla. "
            "Probar fruta de temporada es una forma divertida de conocer la cultura local. Después de comprar, "
            "puedes preparar una comida económica en tu piso compartido. Los mercados también enseñan vocabulario "
            "de cocina que te servirá en restaurantes y supermercados."
        ),
        "en": (
            "La Boqueria is one of Barcelona's most famous markets and a perfect place to practice Spanish "
            "with vendors. Arrive early if you want to avoid crowds and find very fresh fish and fruit. "
            "Many stalls show prices per kilo; watch the scale and ask if you do not understand the weight. "
            "It is normal to greet with a «good morning» before ordering. In other neighborhoods you will find quieter municipal markets "
            "that are often cheaper. Bring a reusable bag and cash in case the card fails. "
            "Trying seasonal fruit is a fun way to learn local culture. After shopping, "
            "you can prepare an economical meal in your shared flat. Markets also teach kitchen vocabulary "
            "that will help you in restaurants and supermarkets."
        ),
    },
    {
        "id": "universidad",
        "lang": "es",
        "title": "Estudiar en la universidad española",
        "body": (
            "El sistema universitario en España puede parecer distinto si vienes de otro país. "
            "Al inicio del semestre debes completar la matrícula y recoger tu carnet de estudiante. "
            "Los profesores suelen publicar materiales en plataformas digitales; revisa el calendario de exámenes "
            "desde el primer día. La asistencia no siempre es obligatoria, pero participar en clase mejora la nota final. "
            "Los trabajos en grupo son frecuentes; acuerda reuniones claras y reparte tareas por escrito. "
            "La biblioteca del campus es un refugio silencioso para estudiar, aunque en época de exámenes hay mucha presión. "
            "Si necesitas adaptaciones por idioma, pregunta en la secretaría académica. Las becas y el intercambio "
            "tienen plazos estrictos, así que organiza la documentación con antelación. Con organización y preguntas "
            "a compañeros locales, adaptarse al ritmo académico es totalmente posible."
        ),
        "en": (
            "The university system in Spain may seem different if you come from another country. "
            "At the start of the semester you must complete enrollment and pick up your student ID. "
            "Professors usually publish materials on digital platforms; check the exam calendar "
            "from day one. Attendance is not always mandatory, but participating in class improves the final grade. "
            "Group projects are common; agree on clear meetings and divide tasks in writing. "
            "The campus library is a quiet refuge for studying, although during exam season there is a lot of pressure. "
            "If you need accommodations for language, ask at the academic office. Scholarships and exchange programs "
            "have strict deadlines, so organize paperwork in advance. With organization and questions "
            "to local classmates, adapting to the academic pace is entirely possible."
        ),
    },
    {
        "id": "alquilar-piso",
        "lang": "es",
        "title": "Alquilar un piso en Barcelona",
        "body": (
            "Encontrar piso en Barcelona requiere paciencia y documentación lista. "
            "Muchos estudiantes comparten piso para reducir gastos; pregunta qué incluye el alquiler: agua, internet, "
            "comunidad de vecinos. El casero puede pedir una fianza equivalente a uno o dos meses. "
            "Lee el contrato con calma y comprueba la duración, las visitas y las reglas sobre mascotas o fiestas. "
            "Las agencias inmobiliarias cobran honorarios; compara varias opciones antes de firmar. "
            "Visita el barrio de noche y de día para evaluar ruido y transporte. Guarda recibos de alquiler y facturas; "
            "te servirán para trámites administrativos. Si hay averías, comunícalo por escrito al casero. "
            "Empadronarte en la vivienda facilita muchos trámites oficiales. Un piso bien elegido hace que tu "
            "experiencia en la ciudad sea más estable y menos estresante."
        ),
        "en": (
            "Finding a flat in Barcelona requires patience and ready documentation. "
            "Many students share a flat to reduce costs; ask what the rent includes: water, internet, "
            "building fees. The landlord may ask for a deposit equal to one or two months. "
            "Read the contract carefully and check duration, visits, and rules about pets or parties. "
            "Estate agencies charge fees; compare several options before signing. "
            "Visit the neighborhood at night and during the day to assess noise and transport. Keep rent receipts and bills; "
            "they will help with administrative procedures. If there are breakdowns, notify the landlord in writing. "
            "Registering your address at the flat facilitates many official procedures. A well-chosen flat makes your "
            "experience in the city more stable and less stressful."
        ),
    },
    {
        "id": "catalan",
        "lang": "es",
        "title": "Entender el catalán en la calle",
        "body": (
            "En Barcelona oirás catalán en carteles, anuncios del metro y conversaciones cotidianas. "
            "No necesitas hablarlo con fluidez para vivir bien, pero reconocer palabras básicas ayuda mucho. "
            "«Sortida» significa salida y «entrada» significa entrada; las verás en estaciones y edificios públicos. "
            "Mucha gente cambia al castellano si les hablas en español. En la universidad encontrarás documentos "
            "bilingües; pide una versión en castellano si lo necesitas. Aprender saludos en catalán es un gesto "
            "amable: «bon dia», «gràcies». Los medios locales mezclan ambos idiomas. No confundas el catalán con "
            "un dialecto «incorrecto»; es una lengua oficial con su propia cultura. Con el tiempo, las señales "
            "repetidas se vuelven familiares y reduces la sensación de estar perdido en la ciudad."
        ),
        "en": (
            "In Barcelona you will hear Catalan on signs, metro announcements, and everyday conversations. "
            "You do not need to speak it fluently to live well, but recognizing basic words helps a lot. "
            "«Sortida» means exit and «entrada» means entrance; you will see them in stations and public buildings. "
            "Many people switch to Spanish if you speak to them in Spanish. At university you will find bilingual documents; "
            "ask for a Spanish version if you need it. Learning greetings in Catalan is a kind gesture: "
            "«bon dia», «gràcies». Local media mix both languages. Do not mistake Catalan for "
            "an «incorrect» dialect; it is an official language with its own culture. Over time, repeated signs "
            "become familiar and you reduce the feeling of being lost in the city."
        ),
    },
    {
        "id": "merce",
        "lang": "es",
        "title": "La Mercè: fiesta mayor de Barcelona",
        "body": (
            "La Mercè es la fiesta mayor de la ciudad y llena las calles de música, fuegos artificiales y actividades gratis. "
            "Suele celebrarse a finales de septiembre; consulta el programa con antelación porque hay cientos de eventos. "
            "Los conciertos en parques públicos son muy populares; llega pronto si quieres buen sitio. "
            "Algunas calles se cierran al tráfico; planifica tu ruta en metro o a pie. "
            "Es una oportunidad excelente para escuchar castellano y catalán en anuncios y presentaciones. "
            "Si no te gustan las multitudes, busca actividades en barrios alejados del centro. "
            "Ten cuidado con carteristas en zonas muy concurridas. Bebe agua y usa protección solar en eventos diurnos. "
            "Participar en La Mercè te conecta con la vida cultural real de Barcelona más allá de los monumentos turísticos."
        ),
        "en": (
            "La Mercè is the city's main festival and fills the streets with music, fireworks, and free activities. "
            "It is usually celebrated at the end of September; check the program in advance because there are hundreds of events. "
            "Concerts in public parks are very popular; arrive early if you want a good spot. "
            "Some streets close to traffic; plan your route by metro or on foot. "
            "It is an excellent opportunity to hear Spanish and Catalan in announcements and presentations. "
            "If you do not like crowds, look for activities in neighborhoods away from the center. "
            "Be careful with pickpockets in very busy areas. Drink water and use sun protection at daytime events. "
            "Taking part in La Mercè connects you with Barcelona's real cultural life beyond tourist monuments."
        ),
    },
    {
        "id": "sant-jordi",
        "lang": "es",
        "title": "Sant Jordi: libros y rosas",
        "body": (
            "El día de Sant Jordi, el 23 de abril, Barcelona se transforma con puestos de libros y rosas en las aceras. "
            "Es tradición regalar una rosa y un libro a familiares o pareja. Las Ramblas y el Passeig de Gràcia "
            "se llenan de gente, pero también hay librerías pequeñas en muchos barrios. "
            "Es un buen momento para practicar español pidiendo recomendaciones al librero. "
            "Algunas universidades organizan actividades culturales ese día. Lleva efectivo por si un puesto no acepta tarjeta. "
            "Si estudias literatura o historia, encontrarás ediciones especiales y firmas de autores. "
            "Aunque el día es festivo en el calendario cultural, las clases pueden continuar; revisa el horario del campus. "
            "Sant Jordi muestra cómo Cataluña mezcla tradición, lengua y vida pública de forma muy visible."
        ),
        "en": (
            "On Sant Jordi's day, April 23, Barcelona transforms with book and rose stalls on the sidewalks. "
            "It is traditional to give a rose and a book to family or a partner. Las Ramblas and Passeig de Gràcia "
            "fill with people, but there are also small bookshops in many neighborhoods. "
            "It is a good time to practice Spanish by asking the bookseller for recommendations. "
            "Some universities organize cultural activities that day. Bring cash in case a stall does not accept cards. "
            "If you study literature or history, you will find special editions and author signings. "
            "Although the day is a cultural holiday, classes may continue; check the campus schedule. "
            "Sant Jordi shows how Catalonia mixes tradition, language, and public life in a very visible way."
        ),
    },
    {
        "id": "salud-cap",
        "lang": "es",
        "title": "Salud pública: el CAP y la tarjeta sanitaria",
        "body": (
            "Como residente o estudiante en España conviene conocer el sistema de atención primaria. "
            "El CAP es el centro de salud de tu barrio donde atiende el médico de cabecera. "
            "Para pedir cita sueles usar la app o llamar por teléfono; en urgencias leves también hay visita sin cita. "
            "La tarjeta sanitaria identifica tu derecho a atención pública si cumples requisitos. "
            "Lleva documento de identidad y empadronamiento cuando tramites el alta. "
            "Las farmacias pueden orientarte sobre productos sin receta, pero no sustituyen una consulta seria. "
            "Si el profesor de la universidad habla de «baja médica», es el certificado de incapacidad temporal. "
            "Guarda informes y recetas en una carpeta digital. En temporada de gripe, los centros van saturados; "
            "sé paciente y llega con vocabulario básico de síntomas para explicar cómo te sientes."
        ),
        "en": (
            "As a resident or student in Spain it is worth knowing the primary care system. "
            "The CAP is your neighborhood health center where the GP sees patients. "
            "To request an appointment you usually use the app or call by phone; for minor urgent issues there is also walk-in care. "
            "The health card identifies your right to public care if you meet requirements. "
            "Bring ID and municipal registration when you register. "
            "Pharmacies can guide you on over-the-counter products, but they do not replace a serious consultation. "
            "If a university professor mentions «sick leave», it is the temporary disability certificate. "
            "Keep reports and prescriptions in a digital folder. During flu season, centers are busy; "
            "be patient and arrive with basic symptom vocabulary to explain how you feel."
        ),
    },
    {
        "id": "banca",
        "lang": "es",
        "title": "Dinero y banca en España",
        "body": (
            "Abrir una cuenta bancaria facilita pagar el alquiler, recibir becas y evitar comisiones por retiradas. "
            "Los bancos suelen pedir pasaporte, NIE o TIE, empadronamiento y a veces un certificado de matrícula. "
            "Compara cuentas para estudiantes sin comisiones de mantenimiento. "
            "Bizum es muy popular para pagos entre personas; te pedirán vincular el móvil. "
            "En muchos comercios puedes pagar con tarjeta, pero en mercados pequeños conviene llevar efectivo. "
            "Revisa el tipo de cambio si recibes dinero del extranjero. "
            "Guarda los comprobantes de transferencias al casero. Si pierdes la tarjeta, bloquéala desde la app inmediatamente. "
            "Aprender vocabulario de finanzas — recibo, deuda, ingreso — te ayuda en trámites universitarios y de alquiler."
        ),
        "en": (
            "Opening a bank account makes it easier to pay rent, receive scholarships, and avoid withdrawal fees. "
            "Banks usually ask for passport, NIE or TIE, municipal registration, and sometimes an enrollment certificate. "
            "Compare student accounts with no maintenance fees. "
            "Bizum is very popular for payments between people; they will ask you to link your phone. "
            "In many shops you can pay by card, but in small markets it is wise to carry cash. "
            "Check the exchange rate if you receive money from abroad. "
            "Keep transfer receipts for the landlord. If you lose your card, block it from the app immediately. "
            "Learning finance vocabulary — receipt, debt, income — helps with university and rental procedures."
        ),
    },
    {
        "id": "renfe-rodalies",
        "lang": "es",
        "title": "Renfe y Rodalies: trenes de cercanías",
        "body": (
            "Además del metro, muchos estudiantes usan Rodalies para ir a Sants, el campus en Bellaterra o pueblos de la costa. "
            "Compra el billete en máquinas o apps indicando origen y destino; conserva el ticket hasta salir. "
            "En hora punta los andenes están llenos; espera detrás de la línea amarilla. "
            "Los retrasos se anuncian en pantallas; aprende palabras como «incidencia» y «cancelación». "
            "Si tienes abono multizona, verifica que cubre el trayecto que haces cada día. "
            "Las conexiones con metro suelen pasan por estaciones grandes; sigue señales de transbordo. "
            "Para excursiones de fin de semana, reserva con antelación en trenes regionales. "
            "Lleva auriculares pero mantén atención a anuncios por si cambia el andén. "
            "Dominar cercanías amplía dónde puedes vivir y estudiar sin depender solo del metro urbano."
        ),
        "en": (
            "Besides the metro, many students use Rodalies to go to Sants, the campus in Bellaterra, or coastal towns. "
            "Buy your ticket at machines or apps indicating origin and destination; keep the ticket until you exit. "
            "At rush hour platforms are crowded; wait behind the yellow line. "
            "Delays are announced on screens; learn words like «incident» and «cancellation». "
            "If you have a multi-zone pass, check that it covers the trip you make each day. "
            "Connections with the metro usually go through large stations; follow transfer signs. "
            "For weekend trips, book regional trains in advance. "
            "Bring headphones but pay attention to announcements in case the platform changes. "
            "Mastering commuter trains expands where you can live and study without relying only on the urban metro."
        ),
    },
    {
        "id": "barrios",
        "lang": "es",
        "title": "Barrios de Barcelona para vivir y estudiar",
        "body": (
            "Elegir barrio influye en precio, ambiente y tiempo de transporte. "
            "Gràcia es popular entre estudiantes por sus plazas y bares, pero el alquiler sube cada año. "
            "Poble-sec y Sant Antoni ofrecen buena conexión al centro y mercados locales. "
            "Eixample tiene calles amplias y muchas líneas de metro, ideal si valoras luz natural. "
            "Poblenou combina playa cercana y espacios de coworking. "
            "Horta y Nou Barris suelen ser más económicos, con más trayecto hasta el campus. "
            "Visita varios pisos antes de decidir; fotos online no muestran ruido nocturno. "
            "Pregunta a vecinos sobre seguridad y limpieza en la calle. "
            "Conocer tu barrio — panadería, farmacia, supermercado — hace la vida diaria más cómoda "
            "y te da contexto real para practicar español fuera de clase."
        ),
        "en": (
            "Choosing a neighborhood affects price, atmosphere, and commute time. "
            "Gràcia is popular among students for its squares and bars, but rent rises every year. "
            "Poble-sec and Sant Antoni offer good connections to the center and local markets. "
            "Eixample has wide streets and many metro lines, ideal if you value natural light. "
            "Poblenou combines nearby beach and coworking spaces. "
            "Horta and Nou Barris are usually more economical, with a longer trip to campus. "
            "Visit several flats before deciding; online photos do not show night noise. "
            "Ask neighbors about safety and street cleanliness. "
            "Knowing your neighborhood — bakery, pharmacy, supermarket — makes daily life more comfortable "
            "and gives you real context to practice Spanish outside class."
        ),
    },
    {
        "id": "empadronamiento",
        "lang": "es",
        "title": "Empadronamiento y trámites en el ayuntamiento",
        "body": (
            "El empadronamiento registra dónde vives y es clave para muchos trámites en Barcelona. "
            "Necesitas contrato de alquiler o autorización del casero, pasaporte y a veces cita previa online. "
            "En la oficina municipal te darán un certificado que sirve para sanidad, banco o becas. "
            "Si cambias de piso, debes actualizar el empadronamiento en plazo. "
            "Sin este paso, otros procesos como el NIE o la tarjeta sanitaria se complican. "
            "Lleva copias impresas y originales; las normas pueden cambiar según tu situación migratoria. "
            "Pide cita en horario de mañana para evitar colas largas. "
            "El personal atiende en castellano y a menudo en catalán; prepara frases simples para explicar tu caso. "
            "Organizar papeles desde el primer mes te ahorra estrés cuando la universidad o el trabajo pidan certificados oficiales."
        ),
        "en": (
            "Municipal registration records where you live and is key for many procedures in Barcelona. "
            "You need a rental contract or landlord authorization, passport, and sometimes an online appointment. "
            "At the municipal office you will receive a certificate useful for healthcare, banking, or scholarships. "
            "If you move, you must update registration on time. "
            "Without this step, other processes such as NIE or health card become complicated. "
            "Bring printed and original copies; rules may change depending on your immigration status. "
            "Book a morning appointment to avoid long queues. "
            "Staff serve in Spanish and often in Catalan; prepare simple phrases to explain your case. "
            "Organizing paperwork from the first month saves stress when university or work ask for official certificates."
        ),
    },
]

# Pad flashcards to exactly 200 if short
while len(FLASHCARD_PAIRS) < 200:
    i = len(FLASHCARD_PAIRS)
    FLASHCARD_PAIRS.append((f"expresión útil {i+1}", f"useful expression {i+1}"))

FLASHCARD_PAIRS = FLASHCARD_PAIRS[:200]

out = Path(__file__).resolve().parent.parent / "fetcher_seeds.py"
lines = [
    '"""Seed data for Estudio Abroad — imported by fetcher.py."""',
    "",
    "FLASHCARD_DECK_SEED = [",
]
for es, en in FLASHCARD_PAIRS:
    lines.append(f'    {{"es": {es!r}, "en": {en!r}}},')
lines.append("]")
lines.append("")
lines.append("DAILY_SENTENCES_ES = [")
for s in DAILY_SENTENCES_ES:
    lines.append(f"    {s!r},")
lines.append("]")
lines.append("")
lines.append("DAILY_PHRASES_ES = [")
for s in DAILY_PHRASES_ES:
    lines.append(f"    {s!r},")
lines.append("]")
lines.append("")
lines.append("READER_PASSAGES_SEED = [")
for p in READER_PASSAGES:
    lines.append("    {")
    lines.append(f'        "id": {p["id"]!r},')
    lines.append(f'        "lang": {p["lang"]!r},')
    lines.append(f'        "title": {p["title"]!r},')
    lines.append(f'        "body": (')
    lines.append(f'            {p["body"]!r}')
    lines.append("        ),")
    lines.append(f'        "en": (')
    lines.append(f'            {p["en"]!r}')
    lines.append("        ),")
    lines.append("    },")
lines.append("]")
lines.append("")

out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out} — cards={len(FLASHCARD_PAIRS)}, sentences={len(DAILY_SENTENCES_ES)}, phrases={len(DAILY_PHRASES_ES)}, passages={len(READER_PASSAGES)}")
