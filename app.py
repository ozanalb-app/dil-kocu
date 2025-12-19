import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import json
import os
import random
import io
import time
import re
from datetime import datetime

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pınar's Friend v20", page_icon="🎭", layout="wide")
DATA_FILE = "user_data.json"

# --- HALÜSİNASYON FİLTRESİ ---
BANNED_PHRASES = [
    "Hi, how are you?", "Good to see you", "Thank you", "Thanks for watching", 
    "Copyright", "Subscribe", "Amara.org", "Watch this video", "You", 
    "I could not think of anything", "Silence", "Bye", "MBC", "Al Jazeera",
    "Caption", "Subtitle"
]

# --- 2. GÜNCELLENMİŞ SENARYO HAVUZU (AKSİYON ODAKLI) ---
SCENARIO_POOL = [
    # A2 - Basic Survival
    "Coffee Shop: Ordering a Latte with Oat Milk",
    "Hotel Reception: Checking in and Asking for Wi-Fi",
    "Street: Asking a Stranger for Directions to the Metro",
    "Restaurant: Asking for a Menu and Water",
    "Shop: Asking for the Price of a T-Shirt",
    "Pharmacy: Buying Aspirin for a Headache",
    "Taxi: Telling the Driver Where to Go",
    "Supermarket: Asking Where the Milk is",
    "Library: Registering for a Membership Card",
    "Cinema: Buying Two Tickets for a Comedy",
    
    # B1 - Intermediate Interactions
    "Clothing Store: Returning a Defective Shirt",
    "Restaurant: Complaining About Cold Food",
    "Train Station: Buying a Ticket and Asking for Platform",
    "Doctor's Office: Describing Symptoms (Fever/Cough)",
    "Hotel: Complaining About Noise from Next Door",
    "Airport Check-in: Requesting a Window Seat",
    "Job Interview: Answering 'Tell me about your experience'",
    "Bank: Opening a New Account",
    "Police Station: Reporting a Lost Wallet",
    "Tech Support: Internet Connection is Not Working",
    
    # B2 - Complex Negotiations
    "Work: Negotiating a Deadline Extension with Boss",
    "Real Estate: Viewing an Apartment and Asking Details",
    "Car Rental: Negotiating Insurance Costs",
    "University: Asking a Professor for Feedback",
    "Insurance Company: Reporting a Car Accident",
    "Work: Resolving a Conflict with a Colleague",
    "Service: Canceling a Gym Membership (Hard Sell)",
    "Customs/Immigration: Explaining Purpose of Visit",
    "Event: Networking and Introducing Yourself",
    "Store: Haggle over the price of an antique"
]

# (Kelime havuzu aynı kalıyor, sadece örnek olsun diye kısa tutuyorum, önceki tam listeyi kullanabilirsin)
VOCAB_POOL = {
    "A2": ["accept", "accident", "address", "adventure", "agree", "airport", "allow", "angry", "answer", "appointment", "arrive", "ask", "bag", "bill", "borrow", "bread", "break", "breakfast", "bridge", "bus", "business", "buy", "calendar", "call", "camera", "card", "carry", "cash", "catch", "change", "cheap", "check", "chef", "choose", "clean", "climb", "clothes", "coat", "cold", "collect", "colour", "comb", "come", "comfortable", "company", "complain", "complete", "concert", "conversation", "cook", "corner", "correct", "cost", "country", "course", "credit", "cross", "crowd", "cry", "cup", "customer", "cut", "daily", "damage", "dance", "danger", "dangerous", "dark", "date", "daughter", "day", "dead", "deal", "dear", "decide", "decision", "deep", "degree", "delay", "dentist", "department", "departure", "depend", "describe", "desk", "destroy", "detail", "diary", "dictionary", "die", "diet", "difference", "different", "difficult", "difficulty", "dig", "dinner", "dirty", "discuss", "dish", "doctor", "dog", "dollar", "door", "double", "doubt", "down", "draw", "dream", "dress", "drink", "drive", "driver", "drop", "drug", "dry", "during"],
    "B1": ["abroad", "absolute", "accept", "access", "accommodation", "accompany", "according", "account", "achieve", "act", "action", "active", "activity", "actually", "adapt", "add", "addition", "admire", "admission", "admit", "adult", "advance", "advantage", "adventure", "advertise", "advertisement", "advice", "advise", "afford", "afraid", "after", "afternoon", "afterwards", "again", "against", "age", "aged", "agency", "agent", "aggressive", "ago", "agree", "agreement", "ahead", "aid", "aim", "air", "aircraft", "airline", "airport", "alarm", "alcohol", "alive", "all", "allow", "ally", "almost", "alone", "along", "alongside", "aloud", "alphabet", "already", "also", "alter", "alternative", "although", "altogether", "always", "amaze", "amazed", "amazing", "ambition", "ambulance", "among", "amount", "amuse", "amused", "amusing", "analyse", "analysis", "ancient", "and", "anger", "angle", "angry", "animal", "ankle", "anniversary", "announce", "announcement", "annoy", "annoyed", "annoying", "annual", "annually", "another", "answer", "anti", "anticipate", "anxiety", "anxious", "any", "anybody", "anyone", "anything", "anyway"],
    "B2": ["abandon", "abbey", "ability", "abolish", "abortion", "about", "above", "absence", "absorb", "abstract", "absurd", "abundance", "abuse", "academic", "academy", "accelerate", "accent", "acceptable", "acceptance", "accessible", "accident", "accidentally", "accommodate", "accomplish", "accordance", "accordingly", "accountability", "accountable", "accountant", "accounting", "accumulate", "accumulation", "accuracy", "accurate", "accusation", "accuse", "accused", "achievement", "acid", "acknowledge", "acquire", "acquisition", "acre", "acrobat", "across", "activate", "activist", "actor", "actress", "actual", "acute", "adaptation", "addict", "addiction", "additional", "additionally", "address", "adequate", "adequately", "adhere", "adjacent", "adjust", "adjustment", "administer", "administration", "administrative", "administrator", "admiration", "admission", "adolescent", "adoption", "advance", "advanced", "adverse", "advertising", "adviser", "advocacy", "advocate", "aerial", "aesthetic", "affair", "affect", "affection", "affluent", "affordable", "aftermath", "agenda", "aggravate", "aggression", "aggressively", "agile", "agitate", "agonize", "agreeable", "agricultural", "agriculture", "aide", "ailment", "aimless", "airborne", "alarm", "alarming", "album", "alcoholic", "alert", "alien", "alienate", "align", "alignment", "alike", "allegation", "allege", "allegedly", "alliance", "allied", "allocate", "allocation", "allowance", "allude", "allure", "ally", "almighty", "alphabetical", "alteration", "alternate", "alternative", "alternatively", "altitude", "altruistic", "aluminum", "amateur", "amazement", "ambassador", "ambiguity", "ambiguous", "ambitious", "ambivalence", "ambivalent", "amenity", "amiable", "amicable", "amid", "amidst", "ammunition", "amnesty", "amount", "ample", "amplification", "amplify", "amusement", "analogy", "analytic", "analytical", "analyze", "anatomy", "ancestor", "anchor", "angel", "angrily", "anguish", "animate", "animation", "animosity", "ankle", "annex", "annihilate", "anniversary", "annotate", "annotation", "announce", "announcer", "annoyance", "annual", "anomaly", "anonymous", "antagonism", "antagonist", "antagonistic", "antagonize", "anticipation", "antidote", "antipathy", "antique", "anxiety", "anxious", "anyhow", "apartheid", "apathetic", "apathy", "ape", "aperture", "apex", "aphorism", "apologetic", "apology", "appall", "appalling", "apparatus", "apparel", "apparent", "apparently", "appeal", "appealing", "appear", "appearance", "appease", "appellate", "append", "appendix", "appetite", "appetizer", "applaud", "applause", "appliance", "applicable", "applicant", "application", "apply", "appoint", "appointment", "appraisal", "appraise", "appreciable", "appreciate", "appreciation", "appreciative", "apprehend", "apprehension", "apprehensive", "apprentice", "apprenticeship", "approach", "appropriate", "appropriation", "approval", "approve", "approximate", "approximately", "approximation", "apron", "apt", "aptitude", "aquarium", "aquatic", "arbitrary", "arbitration", "arbitrator", "arc", "arcade", "arch", "archaeological", "archaeologist", "archaeology", "archaic", "architect", "architectural", "architecture", "archive", "ardent", "arduous", "area", "arena", "arguable", "arguably", "argue", "argument", "argumentative", "arid", "arise", "aristocracy", "aristocrat", "aristocratic", "arithmetic", "arm", "armament", "armed", "armor", "armored", "arms", "army", "aroma", "aromatic", "around", "arouse", "arrange", "arrangement", "array", "arrest", "arrival", "arrive", "arrogance", "arrogant", "arrow", "arsenal", "art", "artery", "artful", "article", "articulate", "articulation", "artifact", "artificial", "artillery", "artisan", "artist", "artistic", "artistry", "artwork", "ascend", "ascension", "ascertain", "ascetic", "ascribe", "ash", "ashamed", "ashore", "aside", "ask", "asleep", "aspect", "aspiration", "aspire", "aspirin", "ass", "assail", "assailant", "assassin", "assassinate", "assassination", "assault", "assemble", "assembly", "assent", "assert", "assertion", "assertive", "assess", "assessment", "asset", "assign", "assignment", "assimilate", "assimilation", "assist", "assistance", "assistant", "associate", "association", "assorted", "assortment", "assume", "assumption", "assurance", "assure", "astonish", "astonishing", "astonishment", "astound", "astounding", "astray", "astrologer", "astrology", "astronaut", "astronomer", "astronomical", "astronomy", "asylum", "at", "athlete", "athletic", "athletics", "atlas", "atmosphere", "atmospheric", "atom", "atomic", "atone", "atonement", "atrocious", "atrocity", "attach", "attachment", "attack", "attacker", "attain", "attainment", "attempt", "attend", "attendance", "attendant", "attention", "attentive", "attic", "attire", "attitude", "attorney", "attract", "attraction", "attractive", "attribute", "attribution", "auction", "audacious", "audacity", "audible", "audience", "audio", "audit", "audition", "auditor", "auditorium", "augment", "augmentation", "august", "aunt", "aura", "auspicious", "austere", "austerity", "authentic", "authenticity", "author", "authoritarian", "authoritative", "authority", "authorization", "authorize", "auto", "autobiography", "autocratic", "autograph", "automate", "automatic", "automatically", "automation", "automobile", "autonomous", "autonomy", "autopsy", "autumn", "auxiliary", "avail", "availability", "available", "avalanche", "avant-garde", "avarice", "avenge", "avenue", "average", "averse", "aversion", "avert", "aviation", "aviator", "avid", "avoid", "avoidance", "await", "awake", "awaken", "award", "aware", "awareness", "away", "awe", "awesome", "awful", "awfully", "awhile", "awkward", "awkwardly", "awkwardness", "awning", "awry", "axe", "axiom", "axis", "axle", "baby", "baccalaureate", "bachelor", "back", "backbone", "backdrop", "backer", "backfire", "background", "backing", "backpack", "backside", "backup", "backward", "backwards", "bacon", "bacteria", "bacterial", "bad", "badge", "badger", "badly", "badminton", "baffle", "bag", "baggage", "baggy", "bail", "bait", "bake", "baker", "bakery", "balance", "balanced", "balcony", "bald", "bale", "ball", "ballad", "ballast", "ballerina", "ballet", "balloon", "ballot", "ballpoint", "balm", "balmy", "bamboo", "ban", "banal", "banana", "band", "bandage", "bandit", "bandwidth", "bang", "bangle", "banish", "banister", "banjo", "bank", "banker", "banking", "bankrupt", "bankruptcy", "banner", "banquet", "baptism", "baptize", "bar", "barbarian", "barbaric", "barbarous", "barbecue", "barbed", "barber", "bare", "barefoot", "barely", "bargain", "barge", "baritone", "bark", "barley", "barn", "barometer", "baron", "baroque", "barracks", "barrage", "barrel", "barren", "barricade", "barrier", "barrister", "barrow", "bartender", "barter", "base", "baseball", "basement", "basic", "basically", "basics", "basin", "basis", "bask", "basket", "basketball", "bass", "bastard", "baste", "bat", "batch", "bath", "bathe", "bathroom", "baton", "battalion", "batter", "battered", "battery", "battle", "battlefield", "battleship", "bawl", "bay", "bayonet", "bazaar", "be", "beach", "beacon", "bead", "beak", "beaker", "beam", "bean", "bear", "bearable", "beard", "bearer", "bearing", "beast", "beat", "beaten", "beating", "beautician", "beautiful", "beautifully", "beautify", "beauty", "beaver", "becalmed", "because", "beckon", "become", "bed", "bedding", "bedlam", "bedroom", "bedside", "bee", "beech", "beef", "beefy", "beehive", "beer", "beet", "beetle", "befall", "befit", "before", "beforehand", "befriend", "beg", "beggar", "begin", "beginner", "beginning", "begrudge", "behalf", "behave", "behavior", "behavioral", "behead", "behind", "behold", "beholder", "beige", "being", "belated", "belch", "belfry", "belief", "believable", "believe", "believer", "belittle", "bell", "belligerent", "bellow", "belly", "belong", "belongings", "beloved", "below", "belt", "bemused", "bench", "benchmark", "bend", "beneath", "benediction", "benefactor", "beneficial", "beneficiary", "benefit", "benevolence", "benevolent", "benign", "bent", "bequeath", "bequest", "berate", "bereaved", "bereavement", "berry", "berth", "beseech", "beset", "beside", "besides", "besiege", "best", "bestow", "bet", "betray", "betrayal", "better", "between", "beverage", "bevy", "bewail", "beware", "bewilder", "bewildered", "bewilderment", "bewitch", "beyond", "bias", "biased", "bib", "bible", "biblical", "bibliography", "bicentennial", "biceps", "bicker", "bicycle", "bid", "bidder", "bidding", "bide", "biennial", "big", "bigot", "bigoted", "bigotry", "bike", "bikini", "bilateral", "bilingual", "bill", "billboard", "billet", "billiards", "billion", "billionaire", "billow", "bin", "binary", "bind", "binder", "binding", "binge", "bingo", "binoculars", "biochemical", "biochemistry", "biographer", "biographical", "biography", "biological", "biologist", "biology", "biopsy", "biotechnology", "bipartisan", "biped", "birch", "bird", "birth", "birthday", "birthplace", "biscuit", "bishop", "bison", "bit", "bitch", "bite", "biting", "bitter", "bitterly", "bitterness", "bizarre", "black", "blackberry", "blackboard", "blacken", "blackmail", "blackout", "blacksmith", "bladder", "blade", "blame", "blameless", "bland", "blank", "blanket", "blare", "blasphemous", "blasphemy", "blast", "blatant", "blaze", "blazer", "bleach", "bleak", "bleary", "bleat", "bleed", "blemish", "blend", "bless", "blessed", "blessing", "blight", "blind", "blindfold", "blindly", "blindness", "blink", "bliss", "blissful", "blister", "blithe", "blizzard", "bloated", "blob", "bloc", "block", "blockade", "blockage", "blog", "blonde", "blood", "bloodshed", "bloodstream", "bloody", "bloom", "blossom", "blot", "blouse", "blow", "blue", "blueberry", "blueprint", "blues", "bluff", "blunder", "blunt", "blur", "blurred", "blurt", "blush", "bluster", "boar", "board", "boarder", "boarding", "boardroom", "boast", "boat", "bob", "bodily", "body", "bodyguard", "bog", "boggle", "bogus", "boil", "boiler", "boisterous", "bold", "boldly", "boldness", "bolster", "bolt", "bomb", "bombard", "bombardment", "bomber", "bombing", "bond", "bondage", "bone", "bonfire", "bonnet", "bonus", "bony", "book", "bookcase", "bookie", "booking", "booklet", "bookmark", "bookseller", "bookshop", "bookstore", "boom", "boomerang", "boon", "boor", "boorish", "boost", "booster", "boot", "booth", "bootleg", "booty", "booze", "border", "borderline", "bore", "bored", "boredom", "boring", "born", "borough", "borrow", "borrower", "bosom", "boss", "bossy", "botanic", "botanical", "botanist", "botany", "botch", "both", "bother", "bottle", "bottleneck", "bottom", "bough", "bought", "boulder", "boulevard", "bounce", "bound", "boundary", "boundless", "bounds", "bounty", "bouquet", "bourgeois", "bourgeoisie", "bout", "boutique", "bovine", "bow", "bowel", "bowl", "box", "boxer", "boxing", "boy", "boycott", "boyfriend", "boyhood", "boyish", "brace", "bracelet", "bracket", "brackish", "brag", "braid", "braille", "brain", "brainchild", "brainless", "brainstorm", "brainwash", "brake", "bran", "branch", "brand", "brandish", "brandy", "brash", "brass", "brat", "bravado", "brave", "bravery", "brawl", "brawn", "brazen", "breach", "bread", "breadth", "break", "breakage", "breakdown", "breaker", "breakfast", "breakthrough", "breakup", "breakwater", "breast", "breath", "breathe", "breathing", "breathless", "breathtaking", "breed", "breeder", "breeding", "breeze", "breezy", "threnody", "brethren", "brevity", "brew", "brewer", "brewery", "bribe", "bribery", "brick", "bricklayer", "bride", "bridegroom", "bridesmaid", "bridge", "bridle", "brief", "briefcase", "briefing", "briefly", "briefs", "brigade", "brigadier", "bright", "brighten", "brightly", "brightness", "brilliant", "brim", "brine", "bring", "brink", "brisk", "briskly", "bristle", "british", "brittle", "broad", "broadcast", "broadcaster", "broadcasting", "broaden", "broadly", "broadside", "brocade", "brochure", "broil", "broke", "broken", "broker", "bronze", "brooch", "brood", "brook", "broom", "broth", "brother", "brotherhood", "brotherly", "brow", "browbeat", "brown", "browse", "browser", "bruise", "brunch", "brunette", "brunt", "brush", "brusque", "brutal", "brutality", "brute", "bubble", "buck", "bucket", "buckle", "bud", "buddha", "buddhism", "buddy", "budge", "budget", "budgetary", "buff", "buffalo", "buffer", "buffet", "buffoon", "bug", "buggy", "bugle", "build", "builder", "building", "buildup", "built", "bulb", "bulge", "bulk", "bulky", "bull", "bulldoze", "bulldozer", "bullet", "bulletin", "bullion", "bullish", "bully", "bulwark", "bum", "bump", "bumper", "bumpy", "bun", "bunch", "bundle", "bungle", "bunk", "bunker", "bunny", "buoy", "buoyant", "burden", "burdensome", "bureau", "bureaucracy", "bureaucrat", "bureaucratic", "burglar", "burglary", "burial", "burlesque", "burly", "burn", "burner", "burning", "burnish", "burrow", "burst", "bury", "bus", "bush", "bushel", "bushy", "business", "businessman", "businesswoman", "bust", "bustle", "busy", "but", "butcher", "butler", "butt", "butter", "butterfly", "buttock", "button", "buttress", "buy", "buyer", "buzz", "buzzer", "by", "bye", "bygone", "bylaw", "bypass", "byproduct", "bystander", "cab", "cabaret", "cabbage", "cabin", "cabinet", "cable", "cacao", "cache", "cackle", "cactus", "cadence", "cadet", "cafe", "cafeteria", "caffeine", "cage", "cagey", "cairn", "cake", "calamitous", "calamity", "calcify", "calculate", "calculated", "calculation", "calculator", "calendar", "calf", "caliber", "calibrate", "calibration", "calico", "call", "caller", "calligraphy", "calling", "callous", "calm", "calmly", "calmness", "calorie", "calumny", "camaraderie", "camel", "cameo", "camera", "cameraman", "camouflage", "camp", "campaign", "campaigner", "camper", "camping", "campus", "can", "canal", "canary", "cancel", "cancellation", "cancer", "candid", "candidacy", "candidate", "candied", "candle", "candlelight", "candor", "candy", "cane", "canine", "canister", "canker", "cannabis", "cannibal", "cannon", "canoe", "canon", "canopy", "cant", "cantankerous", "canteen", "canter", "canvas", "canvass", "canyon", "cap", "capability", "capable", "capacious", "capacity", "cape", "capillary", "capital", "capitalism", "capitalist", "capitalize", "capitulate", "capitulation", "caprice", "capricious", "capsize", "capsule", "captain", "caption", "captivate", "captive", "captivity", "captor", "capture", "car", "caramel", "carat", "caravan", "carbon", "card", "cardboard", "cardiac", "cardigan", "cardinal", "care", "career", "carefree", "careful", "carefully", "careless", "carelessly", "carelessness", "caress", "caretaker", "cargo", "caricature", "carnage", "carnal", "carnation", "carnival", "carnivore", "carnivorous", "carol", "carp", "carpenter", "carpentry", "carpet", "carriage", "carrier", "carrot", "carry", "cart", "cartel", "cartilage", "cartographer", "carton", "cartoon", "cartoonist", "cartridge", "carve", "carving", "cascade", "case", "casement", "cash", "cashew", "cashier", "cashmere", "casing", "casino", "cask", "casket", "cast", "caste", "casting", "castle", "casual", "casually", "casualty", "cat", "cataclysm", "catalog", "catalyst", "catapult", "cataract", "catastrophe", "catastrophic", "catch", "catching", "catchy", "catechism", "categorical", "category", "cater", "caterpillar", "cathedral", "catholic", "cattle", "caucus", "cauldron", "causal", "causality", "cause", "caustic", "caution", "cautionary", "cautious", "cautiously", "cavalcade", "cavalier", "cavalry", "cave", "cavern", "cavernous", "cavity", "cease", "ceaseless", "cedar", "cede", "ceiling", "celebrate", "celebrated", "celebration", "celebrity", "celery", "celestial", "celibacy", "celibate", "cell", "cellar", "cello", "cellular", "cement", "cemetery", "censor", "censorship", "censure", "census", "cent", "centaur", "centennial", "center", "central", "centralize", "centrally", "centre", "centric", "centrifugal", "centrifuge", "centrist", "century", "ceramic", "cereal", "cerebral", "ceremonial", "ceremonious", "ceremony", "certain", "certainly", "certainty", "certificate", "certification", "certified", "certify", "cessation", "cession", "chafe", "chaff", "chagrin", "chain", "chair", "chairman", "chairperson", "chairwoman", "chalet", "chalk", "challenge", "challenging", "chamber", "champagne", "champion", "championship", "chance", "chancellor", "chandelier", "change", "changeable", "channel", "chant", "chaos", "chaotic", "chap", "chapel", "chaperon", "chaplain", "chapter", "char", "character", "characteristic", "characterize", "charade", "charcoal", "charge", "chariot", "charisma", "charismatic", "charitable", "charity", "charlatan", "charm", "charming", "chart", "charter", "chary", "chase", "chasm", "chassis", "chaste", "chastise", "chastity", "chat", "chateau", "chatter", "chatty", "chauffeur", "chauvinism", "chauvinist", "cheap", "cheaply", "cheat", "check", "checkbook", "checker", "checkered", "checkout", "checkup", "cheek", "cheeky", "cheer", "cheerful", "cheerfully", "cheerfulness", "cheerless", "cheery", "cheese", "chef", "chemical", "chemist", "chemistry", "cherish", "cherry", "cherub", "chess", "chest", "chestnut", "chevron", "chew", "chic", "chick", "chicken", "chide", "chief", "chiefly", "chieftain", "child", "childbirth", "childhood", "childish", "childlike", "chill", "chilly", "chime", "chimney", "chimpanzee", "chin", "china", "chip", "chirp", "chisel", "chivalrous", "chivalry", "chlorine", "chocolate", "choice", "choir", "choke", "cholera", "choose", "chop", "chopper", "choral", "chord", "chore", "choreography", "chorus", "chosen", "chowder", "christ", "christen", "christian", "christianity", "christmas", "chrome", "chromatic", "chromosome", "chronic", "chronicle", "chronological", "chronology", "chubby", "chuck", "chuckle", "chum", "chunk", "church", "churlish", "churn", "chute", "cider", "cigar", "cigarette", "cinch", "cinder", "cinema", "cipher", "circle", "circuit", "circuitous", "circular", "circulate", "circulation", "circumference", "circumlocution", "circumnavigate", "circumscribe", "circumspect", "circumstance", "circumstantial", "circumvent", "circus", "cistern", "citadel", "citation", "cite", "citizen", "citizenship", "city", "civic", "civil", "civilian", "civility", "civilization", "civilize", "civilized", "clad", "claim", "claimant", "clairvoyant", "clam", "clamber", "clammy", "clamor", "clamp", "clan", "clandestine", "clang", "clank", "clap", "clarification", "clarify", "clarinet", "clarity", "clash", "clasp", "class", "classic", "classical", "classification", "classified", "classify", "classmate", "classroom", "classy", "clatter", "clause", "claustrophobia", "claw", "clay", "clean", "cleaner", "cleaning", "cleanliness", "cleanly", "cleanse", "cleanser", "clear", "clearance", "clearly", "cleave", "cleaver", "clef", "cleft", "clemency", "clement", "clergy", "clergyman", "cleric", "clerical", "clerk", "clever", "cleverly", "cliche", "click", "client", "clientele", "cliff", "climate", "climatic", "climax", "climb", "climber", "climbing", "clinch", "cling", "clinic", "clinical", "clink", "clip", "clipboard", "clipper", "clique", "cloak", "cloakroom", "clock", "clockwise", "clockwork", "clod", "clog", "cloister", "clone", "close", "closed", "closely", "closet", "closure", "clot", "cloth", "clothe", "clothes", "clothing", "cloud", "cloudless", "cloudy", "clout", "clove", "clover", "clown", "cloy", "club", "clue", "clump", "clumsy", "cluster", "clutch", "clutter", "coach", "coagulate", "coal", "coalition", "coarse", "coast", "coastal", "coastguard", "coat", "coating", "coax", "cob", "cobalt", "cobbler", "cobra", "cobweb", "cocaine", "cock", "cockpit", "cockroach", "cocktail", "cocoa", "coconut", "cocoon", "cod", "code", "codify", "coeducation", "coefficient", "coerce", "coercion", "coexist", "coexistence", "coffee", "coffin", "cog", "cogent", "cogitate", "cognac", "cognition", "cognitive", "cognizant", "cohabit", "cohere", "coherence", "coherent", "cohesion", "cohesive", "cohort", "coil", "coin", "coinage", "coincide", "coincidence", "coincident", "coincidental", "coke", "colander", "cold", "coldly", "coldness", "collaborate", "collaboration", "collaborator", "collage", "collapse", "collapsible", "collar", "collate", "collateral", "colleague", "collect", "collection", "collective", "collectively", "collector", "college", "collide", "collision", "colloquial", "colloquium", "collusion", "colon", "colonel", "colonial", "colonialism", "colonist", "colonize", "colony", "colossal", "color", "colorful", "coloring", "colorless", "colossal", "colt", "column", "columnist", "coma", "comb", "combat", "combatant", "combination", "combine", "combustible", "combustion", "come", "comedian", "comedy", "comely", "comet", "comfort", "comfortable", "comfortably", "comforter", "comic", "comical", "coming", "comma", "command", "commandant", "commander", "commanding", "commandment", "commemorate", "commemoration", "commence", "commencement", "commend", "commendable", "comment", "commentary", "commentator", "commerce", "commercial", "commercialize", "commiserate", "commission", "commissioner", "commit", "commitment", "committee", "commodity", "commodore", "common", "commonplace", "commonwealth", "commotion", "communal", "commune", "communicate", "communication", "communicative", "communion", "communique", "communism", "communist", "community", "commute", "commuter", "compact", "companion", "companionship", "company", "comparable", "comparative", "comparatively", "compare", "comparison", "compartment", "compass", "compassion", "compassionate", "compatibility", "compatible", "compatriot", "compel", "compelling", "compendium", "compensate", "compensation", "compete", "competence", "competent", "competition", "competitive", "competitor", "compilation", "compile", "complacency", "complacent", "complain", "complaint", "complement", "complementary", "complete", "completely", "completion", "complex", "complexion", "complexity", "compliance", "compliant", "complicate", "complicated", "complication", "complicity", "compliment", "complimentary", "comply", "component", "comport", "compose", "composer", "composite", "composition", "compost", "composure", "compound", "comprehend", "comprehensible", "comprehension", "comprehensive", "compress", "compression", "comprise", "compromise", "compulsion", "compulsive", "compulsory", "compunction", "computation", "compute", "computer", "computerize", "comrade", "con", "concave", "conceal", "concealment", "concede", "conceit", "conceited", "conceivable", "conceive", "concentrate", "concentration", "concentric", "concept", "conception", "conceptual", "concern", "concerned", "concerning", "concert", "concerted", "concerto", "concession", "conch", "ciliate", "conciliate", "conciliatory", "concise", "conclave", "conclude", "conclusion", "conclusive", "concoct", "concoction", "concomitant", "concord", "concordance", "concourse", "concrete", "cubicle", "concubine", "concur", "conoccurrence", "concurrent", "concussion", "condemn", "condemnation", "condensation", "condense", "condescend", "condescending", "condiment", "condition", "conditional", "conditioning", "condolence", "condone", "conducive", "conduct", "conductor", "conduit", "cone", "confection", "confectionery", "confederacy", "confederate", "confederation", "confer", "conference", "confess", "confession", "confessor", "confetti", "confidant", "confide", "confidence", "confident", "confidential", "confidently", "configuration", "configure", "confine", "confinement", "confirm", "confirmation", "confiscate", "confiscation", "conflagration", "conflict", "confluence", "conform", "conformist", "conformity", "confound", "confront", "confrontation", "confuse", "confused", "confusing", "confusion", "congenial", "congenital", "congested", "congestion", "conglomerate", "congratulate", "congratulation", "congregate", "congregation", "congress", "congressman", "conical", "conjecture", "conjugal", "conjugate", "conjunction", "conjure", "connect", "connection", "connective", "connoisseur", "connote", "conquer", "conqueror", "conquest", "conscience", "conscientious", "conscious", "consciousness", "conscript", "conscription", "consecrate", "consecutive", "consensus", "consent", "consequence", "consequent", "consequently", "conservation", "conservatism", "conservative", "conservatory", "conserve", "consider", "considerable", "considerably", "considerate", "consideration", "considering", "consign", "consignment", "consist", "consistency", "consistent", "consistently", "consolation", "console", "consolidate", "consolidation", "consonant", "consort", "consortium", "conspicuous", "conspiracy", "conspirator", "conspire", "constable", "constancy", "constant", "constantly", "constellation", "consternation", "constipation", "constituency", "constituent", "constitute", "constitution", "constitutional", "constrain", "constraint", "constrict", "constriction", "construct", "construction", "constructive", "construe", "consul", "consular", "consulate", "consult", "consultancy", "consultant", "consultation", "consume", "consumer", "consumption", "contact", "contagious", "contain", "container", "contaminate", "contamination", "contemplate", "contemplation", "contemporary", "contempt", "contemptible", "contemptuous", "contend", "content", "contented", "contention", "contentious", "contentment", "contents", "contest", "contestant", "context", "contiguous", "continent", "continental", "contingency", "contingent", "continual", "continually", "continuance", "continuation", "continue", "continuity", "continuous", "continuously", "contort", "contortion", "contour", "contraband", "contraception", "contraceptive", "contract", "contraction", "contractor", "contradict", "contradiction", "contradictory", "contraption", "contrary", "contrast", "contravene", "contribute", "contribution", "contributor", "contrite", "contrivance", "contrive", "control", "controller", "controversial", "controversy", "convalesce", "convalescence", "convene", "convenience", "convenient", "conveniently", "convent", "convention", "conventional", "converge", "convergence", "conversant", "conversation", "conversational", "converse", "conversion", "convert", "convertible", "convex", "convey", "conveyance", "convict", "conviction", "convince", "convincing", "convivial", "convocation", "convoy", "convulse", "convulsion", "cook", "cookbook", "cooker", "cookie", "cooking", "cool", "coolant", "cooler", "coolly", "coop", "cooper", "cooperate", "cooperation", "cooperative", "coordinate", "coordination", "coordinator", "cop", "cope", "copious", "copper", "copulate", "copy", "copyright", "coral", "cord", "cordial", "cordon", "core", "cork", "corkscrew", "corn", "corner", "cornerstone", "cornet", "cornice", "corolla", "corollary", "corona", "coronation", "coroner", "corporal", "corporate", "corporation", "corporeal", "corps", "corpse", "corpulent", "corpus", "correct", "correction", "corrective", "correctly", "correlate", "correlation", "correspond", "correspondence", "correspondent", "corresponding", "corridor", "corroborate", "corrode", "corrosion", "corrosive", "corrugate", "corrupt", "corruption", "corset", "cortege", "cosmetic", "cosmic", "cosmonaut", "cosmopolitan", "cosmos", "cost", "costly", "costume", "cosy", "cot", "cottage", "cotton", "couch", "cough", "council", "councilor", "counsel", "counseling", "counselor", "count", "countenance", "counter", "counteract", "counterattack", "counterbalance", "counterfeit", "counterpart", "countess", "countless", "country", "countryside", "county", "coup", "couple", "coupon", "courage", "courageous", "courier", "course", "court", "courteous", "courtesy", "courthouse", "courtier", "courtroom", "courtship", "courtyard", "cousin", "cove", "covenant", "cover", "coverage", "covering", "covert", "covet", "cow", "coward", "cowardice", "cowardly", "cowboy", "cower", "coy", "crab", "crack", "crackdown", "cracker", "crackle", "cradle", "craft", "craftsman", "craftsmanship", "crafty", "crag", "cram", "cramp", "cramped", "cranberry", "crane", "cranium", "crank", "cranky", "crap", "crash", "crate", "crater", "cravat", "crave", "craving", "crawl", "crayon", "craze", "crazy", "creak", "creaky", "cream", "creamy", "crease", "create", "creation", "creative", "creativity", "creator", "creature", "credence", "credential", "credibility", "credible", "credit", "creditable", "creditor", "credo", "creed", "creek", "creep", "creepy", "cremate", "cremation", "creole", "crepe", "crescendo", "crescent", "crest", "crestfallen", "crevice", "crew", "crib", "cricket", "crime", "criminal", "crimp", "crimson", "cringe", "cripple", "crisis", "crisp", "criterion", "critic", "critical", "critically", "criticism", "criticize", "critique", "croak", "crochet", "crockery", "crocodile", "crone", "cronies", "crook", "crooked", "crop", "cross", "crossbar", "crossfire", "crossing", "crossroads", "crossword", "crotch", "crouch", "crow", "crowbar", "crowd", "crowded", "crown", "crucial", "crucible", "crucifix", "crucifixion", "crucify", "crude", "cruel", "cruelly", "cruelty", "cruise", "cruiser", "crumb", "crumble", "crumple", "crunch", "crusade", "crusader", "crush", "crust", "crustacean", "crutch", "crux", "cry", "crypt", "cryptic", "crystal", "crystallize", "cub", "cube", "cubic", "cubicle", "cuckoo", "cucumber", "cuddle", "cudgel", "cue", "cuff", "cuisine", "culinary", "cull", "culminate", "culmination", "culpable", "culprit", "cult", "cultivate", "cultivation", "cultural", "culture", "cumbersome", "cumulative", "cunning", "cup", "cupboard", "cupidity", "curable", "curator", "curb", "curd", "curdle", "cure", "curfew", "curio", "curiosity", "curious", "curiously", "curl", "curly", "currant", "currency", "current", "currently", "curriculum", "curry", "curse", "cursory", "curt", "curtail", "curtain", "curvature", "curve", "cushion", "custard", "custodian", "custody", "custom", "customary", "customer", "customs", "cut", "cute", "cuticle", "cutlery", "cutlet", "cutter", "cutting", "cycle", "cyclic", "cyclist", "cyclone", "cylinder", "cymbal", "cynic", "cynical", "cynicism", "cypress", "cyst", "czar"]
}

# --- 3. YARDIMCI FONKSİYONLAR ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "current_level": "A2", 
            "lessons_completed": 0, 
            "exam_scores": [], 
            "vocabulary_bank": [], 
            "completed_scenarios": [],
            "rotated_vocab": {"A2": [], "B1": [], "B2": []},
            "lesson_history": [],
            "error_bank": [],
            "next_mode": "ASSESSMENT",
            "next_lesson_prep": None 
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        defaults = {
            "completed_scenarios": [], 
            "error_bank": [],
            "next_lesson_prep": None,
            "rotated_vocab": {"A2": [], "B1": [], "B2": []},
            "lesson_history": []
        }
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def strict_json_parse(text):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except:
        return {}

def determine_sub_level(level, lessons_completed):
    cycle = lessons_completed % 10
    if cycle < 3: return "Low"
    elif cycle < 7: return "Medium"
    else: return "High"

def get_relevant_vocab(client, scenario, available_vocab_list):
    if len(available_vocab_list) <= 5: return available_vocab_list
    candidates = random.sample(available_vocab_list, min(50, len(available_vocab_list)))
    prompt = f"SCENARIO: {scenario}\nCANDIDATES: {', '.join(candidates)}\nSelect 5 relevant words. JSON ARRAY ONLY: ['w1', ...]"
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return strict_json_parse(res.choices[0].message.content)
    except:
        return random.sample(candidates, 5)

user_data = load_data()

# --- 4. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_minutes):
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level_desc = f"{level} ({sub_level})"
    
    assigned_scenario = None
    assigned_vocab = []
    
    if mode == "LESSON" and user_data.get("next_lesson_prep"):
        plan = user_data["next_lesson_prep"]
        assigned_scenario = plan.get("scenario", plan.get("topic"))
        assigned_vocab = plan.get("vocab", [])
        st.toast(f"📅 Planned Scenario: {assigned_scenario}", icon="✅")

    # 🔥 ROL TANIMLAMALARI (DİNAMİK)
    if mode == "EXAM":
        scenario = random.choice(SCENARIO_POOL)
        system_role = f"ACT AS: Strict Examiner. LEVEL: {full_level_desc}. SCENARIO: {scenario}. CRITICAL: Ask concise questions. Do not give feedback."
    elif mode == "ASSESSMENT":
        scenario = "Placement Interview"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions ONE BY ONE."
    else:
        if assigned_scenario:
            scenario = assigned_scenario
        else:
            completed = user_data.get("completed_scenarios", [])
            available = [s for s in SCENARIO_POOL if s not in completed]
            if not available:
                user_data["completed_scenarios"] = []
                save_data(user_data)
                available = SCENARIO_POOL
            scenario = random.choice(available)
            if scenario not in user_data["completed_scenarios"]:
                user_data["completed_scenarios"].append(scenario)
                save_data(user_data)

        # 🔥 ROL ÜRETİCİ
        system_role = f"""
        YOU ARE A REALISTIC ROLEPLAY PARTNER. 
        SCENARIO: '{scenario}'. 
        USER LEVEL: {full_level_desc}.
        
        INSTRUCTIONS:
        1. Adapt your speed and vocabulary to {full_level_desc}.
        2. Keep replies SHORT (max 25 words).
        3. ALWAYS ask a follow-up question to keep the conversation flowing.
        4. NEVER say "Good job" or break character.
        """

    target_vocab = []
    if mode == "LESSON":
        if assigned_vocab: target_vocab = assigned_vocab
        else:
            full_list = VOCAB_POOL.get(level, [])
            used = user_data["rotated_vocab"].get(level, [])
            avail = [w for w in full_list if w not in used]
            if len(avail) < 5:
                user_data["rotated_vocab"][level] = []
                avail = full_list
                save_data(user_data)
            target_vocab = get_relevant_vocab(client, scenario, avail)

    st.session_state.lesson_active = True
    st.session_state.reading_phase = False
    st.session_state.reading_completed = False
    st.session_state.final_report = None
    st.session_state.accumulated_speaking_time = 0.0 
    st.session_state.target_speaking_seconds = target_speaking_minutes * 60 
    st.session_state.target_vocab = target_vocab
    st.session_state.scenario = scenario
    st.session_state.last_audio_bytes = None
    
    # 📌 CONTEXT SETTER (BAŞLANGIÇ MESAJI)
    context_setter = f"""
    📍 **SCENARIO:** {scenario}
    🎯 **GOAL:** Practice {full_level_desc} speaking.
    🔑 **TARGET WORDS:** {', '.join(target_vocab).upper()}
    
    *I will start the roleplay now.*
    """
    
    # İlk mesajı üret (AI başlasın)
    ai_start_prompt = f"{system_role}\nStart the roleplay now with your first line."
    
    try:
        # Önce rolleri açıkla (System message olarak ekle ama kullanıcı görmesin, sadece AI bilsin)
        st.session_state.messages = [{"role": "system", "content": ai_start_prompt}]
        
        # İlk AI cevabını al
        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        first_line = res.choices[0].message.content
        
        # Çevirisini al
        tr_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": f"Translate to Turkish: {first_line}"}])
        tr_line = tr_res.choices[0].message.content
        
        # SOHBET GEÇMİŞİNE EKLE: 1. Context (Bilgi Fişi), 2. İlk Replik
        # Not: Streamlit'te göstermek için mesaj listesine ekliyoruz.
        st.session_state.display_messages = [] # Ekranda gösterilecekler
        st.session_state.display_messages.append({"role": "info", "content": context_setter})
        
        st.session_state.messages.append({"role": "assistant", "content": first_line})
        # Display listesine de ekle (Çeviriyle)
        st.session_state.display_messages.append({"role": "assistant", "content": first_line, "tr_content": tr_line})
        
        tts = gTTS(text=first_line, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.session_state.last_audio_response = fp.getvalue()
        
        if mode == "LESSON" and user_data.get("next_lesson_prep"):
            user_data["next_lesson_prep"] = None
            save_data(user_data)
            
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")
        st.session_state.lesson_active = False

# --- 5. ARAYÜZ ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    with st.sidebar:
        api_key = st.text_input("API Key", type="password")

if api_key:
    client = OpenAI(api_key=api_key)
    page = st.sidebar.radio("📌 Menu", ["🎭 Scenario Coach", "👂 Listening Quiz", "🏋️ Vocab Gym", "📜 History"])

    with st.sidebar:
        st.divider()
        st.markdown("### 🚨 Error Bank")
        errors = user_data.get("error_bank", [])
        if not errors: st.caption("No errors recorded yet.")
        else:
            for e in reversed(errors[-3:]):
                st.error(f"❌ {e['wrong']}\n✅ {e['correct']}")
            if len(errors) > 3: st.caption(f"...and {len(errors)-3} more.")
            if st.button("🗑️ Clear"):
                user_data["error_bank"] = []
                save_data(user_data)
                st.rerun()

    # --- LISTENING QUIZ ---
    if page == "👂 Listening Quiz":
        st.title("👂 Listening & Dictation")
        if "quiz_text" not in st.session_state:
            st.session_state.quiz_text = None
            st.session_state.quiz_audio = None
            st.session_state.quiz_checked = False

        if st.button("🔊 New Audio"):
            with st.spinner("Generating..."):
                prompt = f"Generate a B1 level sentence. Just the sentence."
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                text = res.choices[0].message.content.strip().replace('"', '')
                st.session_state.quiz_text = text
                tts = gTTS(text=text, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.session_state.quiz_audio = fp.getvalue()
                st.session_state.quiz_checked = False
                st.rerun()

        if st.session_state.quiz_audio:
            st.audio(st.session_state.quiz_audio, format='audio/mp3')
            user_input = st.text_input("Type what you hear:")
            if st.button("Check"):
                st.session_state.quiz_checked = True
            
            if st.session_state.quiz_checked:
                clean_correct = re.sub(r'[^\w\s]', '', st.session_state.quiz_text).lower()
                clean_user = re.sub(r'[^\w\s]', '', user_input).lower()
                if clean_user == clean_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Correct: {st.session_state.quiz_text}")

    # --- VOCAB GYM ---
    elif page == "🏋️ Vocab Gym":
        st.title("🏋️ Vocabulary Gym")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 New Card"):
                pool = VOCAB_POOL.get(user_data["current_level"], ["hello"])
                pool_copy = list(pool)
                random.shuffle(pool_copy)
                word = random.choice(pool_copy)
                st.session_state.flashcard_word = word
                st.session_state.flashcard_revealed = False
                
                tts = gTTS(text=word, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.session_state.vocab_audio = fp.getvalue()
        
        if "flashcard_word" in st.session_state and st.session_state.flashcard_word:
            st.markdown(f"<h1 style='text-align: center; color:#4F8BF9'>{st.session_state.flashcard_word}</h1>", unsafe_allow_html=True)
            if "vocab_audio" in st.session_state:
                st.audio(st.session_state.vocab_audio, format='audio/mp3', autoplay=True)

            if not st.session_state.flashcard_revealed:
                if st.button("👀 Show Meaning"):
                    st.session_state.flashcard_revealed = True
                    prompt = f"Define '{st.session_state.flashcard_word}' in Turkish + Example. JSON: {{'tr':'...', 'ex':'...'}}"
                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.card_data = strict_json_parse(res.choices[0].message.content)
                    st.rerun()
            else:
                d = st.session_state.card_data
                st.success(f"🇹🇷 {d.get('tr','')}")
                st.info(f"🇬🇧 {d.get('ex','')}")

    # --- HISTORY ---
    elif page == "📜 History":
        st.title("📜 History")
        hist = user_data.get("lesson_history", [])
        if not hist: st.info("No history.")
        for h in reversed(hist):
            with st.expander(f"📚 {h.get('date')} - {h.get('topic')}"):
                st.write(f"**Score:** {h.get('score')}")
                st.caption(f"Speak: {h.get('speaking_score')} | Read: {h.get('reading_score')}")
                st.warning(f"**Grammar Needs:**\n" + "\n".join([f"- {t}" for t in h.get('grammar_topics', [])]))

    # --- SCENARIO COACH ---
    elif page == "🎭 Scenario Coach":
        st.title("🗣️ AI Roleplay Coach")
        with st.sidebar:
            st.divider()
            sub = determine_sub_level(user_data['current_level'], user_data['lessons_completed'])
            c1, c2 = st.columns(2)
            with c1: st.metric("Level", user_data['current_level'])
            with c2: st.metric("Band", sub)
            
            if st.session_state.get("lesson_active", False) and not st.session_state.get("reading_phase", False):
                curr = st.session_state.accumulated_speaking_time
                targ = st.session_state.target_speaking_seconds
                prog = min(curr/targ, 1.0) if targ > 0 else 0
                c_min = int(curr // 60)
                c_sec = int(curr % 60)
                t_min = int(targ // 60)
                t_sec = int(targ % 60)
                st.progress(prog, text=f"Time: {c_min}m {c_sec}s / {t_min}m {t_sec}s")

        if not st.session_state.get("lesson_active", False):
            if user_data.get("next_lesson_prep"):
                # Güvenli erişim
                prep = user_data.get("next_lesson_prep", {})
                sc_name = prep.get("scenario", prep.get("topic", "Unknown"))
                st.success(f"🎯 Next: {sc_name}")
            mins = st.slider("Duration (Mins)", 0.5, 30.0, 1.0, step=0.5)
            if st.button("🚀 START SCENARIO"):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], mins)
                st.rerun()
        else:
            if not st.session_state.get("reading_phase", False):
                chat_cont = st.container()
                with chat_cont:
                    # 🔥 GÜNCELLENMİŞ EKRAN GÖSTERİMİ
                    # display_messages listesini kullanıyoruz (Info + Chat)
                    disp_msgs = st.session_state.get("display_messages", [])
                    for i, msg in enumerate(disp_msgs):
                        if msg["role"] == "info":
                            st.info(msg["content"])
                        
                        elif msg["role"] == "user":
                            # Hata düzeltmesi varsa göster
                            if "correction" in msg:
                                with st.expander("🛠️ Grammar Check", expanded=True):
                                    st.markdown(f":red[{msg['correction']}]")
                            with st.chat_message("user", avatar="👤"):
                                st.write(msg["content"])
                        
                        elif msg["role"] == "assistant":
                            is_last = (i == len(disp_msgs) - 1)
                            if is_last:
                                with st.chat_message("assistant", avatar="🤖"):
                                    st.write("🔊 **Listening...**")
                                    with st.expander("🇬🇧 Text"):
                                        content = msg["content"]
                                        for w in st.session_state.target_vocab:
                                            content = re.sub(f"(?i)\\b{w}\\b", f"**:{'blue'}[{w.upper()}]**", content)
                                        st.markdown(content)
                                    with st.expander("🇹🇷 Türkçesi"):
                                        st.info(msg.get("tr_content", "..."))
                            else:
                                with st.chat_message("assistant", avatar="🤖"):
                                    st.write(msg["content"])

                if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
                    st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

                st.write("---")
                if st.button("🆘 Hints"):
                    with st.spinner("..."):
                        hist = st.session_state.messages[-4:]
                        prompt = "Give 3 short English reply options suitable for this scenario."
                        res = client.chat.completions.create(model="gpt-4o", messages=hist+[{"role":"user","content":prompt}])
                        st.info(res.choices[0].message.content)

                c1, c2 = st.columns([1,4])
                with c1: audio = mic_recorder(start_prompt="🎤", stop_prompt="⏹️")
                with c2:
                    curr = st.session_state.accumulated_speaking_time
                    targ = st.session_state.target_speaking_seconds
                    if st.button("➡️ READING PHASE", use_container_width=True):
                        if user_data["next_mode"]!="ASSESSMENT" and curr < targ:
                            st.toast("Keep speaking!", icon="⏳")
                        else:
                            st.session_state.reading_phase = True
                            prompt = f"Create A2/B1 reading text about the scenario: {st.session_state.scenario}. Then 3 questions. JSON: {{'text':'...','questions':['Q1','Q2','Q3']}}"
                            res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                            st.session_state.reading_content = strict_json_parse(res.choices[0].message.content)
                            st.rerun()

                if audio:
                    if "last_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_bytes:
                        st.session_state.last_bytes = audio['bytes']
                        if len(audio['bytes']) < 2000:
                            st.warning("Audio unclear. Try again.")
                        else:
                            with st.spinner("Processing..."):
                                try:
                                    bio = io.BytesIO(audio['bytes'])
                                    bio.name = "audio.webm"
                                    txt = client.audio.transcriptions.create(
                                        model="whisper-1", file=bio, language="en", temperature=0.2,
                                        prompt=f"User speaking about scenario {st.session_state.scenario}."
                                    ).text
                                    
                                    bad = any(b.lower() in txt.lower() for b in BANNED_PHRASES)
                                    if bad or len(txt.strip()) < 2:
                                        st.warning("Audio unclear.")
                                    else:
                                        st.session_state.accumulated_speaking_time += len(txt.split()) * 0.7
                                        
                                        corr = None
                                        try:
                                            p_check = f"Check '{txt}'. IGNORE small errors. If MAJOR error, return 'Düzeltme: [Correct]'. Else 'OK'."
                                            c_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p_check}])
                                            ans = c_res.choices[0].message.content
                                            if "Düzeltme:" in ans:
                                                corr = ans
                                                user_data["error_bank"].append({"wrong": txt, "correct": corr.replace("Düzeltme:", "").strip()})
                                                save_data(user_data)
                                        except: pass

                                        # Ana mesaj listesine ekle
                                        u_msg = {"role": "user", "content": txt}
                                        st.session_state.messages.append(u_msg)
                                        
                                        # Display listesine ekle (Düzeltme ile)
                                        disp_u_msg = {"role": "user", "content": txt}
                                        if corr: disp_u_msg["correction"] = corr
                                        st.session_state.display_messages.append(disp_u_msg)
                                        
                                        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                                        rep = res.choices[0].message.content
                                        tr_rep = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":f"Translate to Turkish: {rep}"}]).choices[0].message.content
                                        
                                        st.session_state.messages.append({"role": "assistant", "content": rep})
                                        st.session_state.display_messages.append({"role": "assistant", "content": rep, "tr_content": tr_rep})
                                        
                                        tts = gTTS(text=rep, lang='en')
                                        fp = io.BytesIO()
                                        tts.write_to_fp(fp)
                                        st.session_state.last_audio_response = fp.getvalue()
                                        st.rerun()
                                except Exception as e: 
                                    st.error(f"Audio Error: {e}")

            # OKUMA FAZI
            else:
                if not st.session_state.get("reading_completed", False):
                    st.markdown("### 📖 Reading")
                    content = st.session_state.get("reading_content", {})
                    st.info(content.get("text", ""))
                    
                    with st.form("read_form"):
                        ans_list = []
                        for i, q in enumerate(content.get("questions", [])):
                            ans_list.append(st.text_input(f"{i+1}. {q}"))
                        submitted = st.form_submit_button("🏁 FINISH")
                    
                    if submitted:
                        with st.spinner("Analyzing..."):
                            prompt = """
                            Analyze Speaking & Reading.
                            SCORING: score = (speak_score*0.8) + (read_score*0.2).
                            FEEDBACK (IN TURKISH): pros, cons, grammar_topics, suggestions.
                            NEXT LESSON: New scenario + 5 words.
                            JSON: {
                                "score": 0, "speaking_score": 0, "reading_score": 0,
                                "reading_feedback": [{"question":"...","user_answer":"...","correct_answer":"...","is_correct":true}],
                                "learned_words": [], "pros": [], "cons": [], "grammar_topics": [], "suggestions": [],
                                "next_lesson_homework": {"scenario": "...", "vocab": []}
                            }
                            """
                            user_json = json.dumps({f"Q{i}": a for i,a in enumerate(ans_list)})
                            msgs = st.session_state.messages + [{"role":"user","content":f"Reading Answers: {user_json}"}, {"role":"system","content":prompt}]
                            
                            res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                            rep = strict_json_parse(res.choices[0].message.content)
                            if not rep: rep = {"score": 70} 

                            user_data["lessons_completed"] += 1
                            user_data["rotated_vocab"][user_data["current_level"]].extend(st.session_state.target_vocab)
                            if "next_lesson_homework" in rep: user_data["next_lesson_prep"] = rep["next_lesson_homework"]
                            
                            hist = {
                                "date": datetime.now().strftime("%Y-%m-%d"),
                                "topic": st.session_state.scenario,
                                "score": rep.get("score"),
                                "speaking_score": rep.get("speaking_score"),
                                "reading_score": rep.get("reading_score"),
                                "grammar_topics": rep.get("grammar_topics", []),
                                "words": st.session_state.target_vocab,
                                "feedback_pros": rep.get("pros", []),
                                "feedback_cons": rep.get("cons", [])
                            }
                            user_data["lesson_history"].append(hist)
                            save_data(user_data)
                            
                            st.session_state.final_report = rep
                            st.session_state.reading_completed = True
                            st.rerun()
                
                else:
                    rep = st.session_state.final_report
                    st.balloons()
                    st.markdown(f"## 📊 Score: {rep.get('score')} (🗣️{rep.get('speaking_score')} | 📖{rep.get('reading_score')})")
                    
                    for fb in rep.get("reading_feedback", []):
                        color = "green" if fb["is_correct"] else "red"
                        with st.expander(f"Question: {fb['question']}"):
                            st.write(f"You: {fb['user_answer']}")
                            st.markdown(f":{color}[Correct: {fb['correct_answer']}]")

                    c1, c2 = st.columns(2)
                    with c1: st.success("\n".join(rep.get('pros', [])))
                    with c2: st.error("\n".join(rep.get('cons', [])))
                    
                    if rep.get('grammar_topics'):
                        st.warning("**Çalış:** " + ", ".join(rep.get('grammar_topics')))
                        
                    # 🔥 FIX: Güvenli erişim
                    next_sc = rep.get('next_lesson_homework', {}).get('scenario', 'Next Level')
                    st.info(f"**Next:** {next_sc}")
                    
                    if st.button("🚀 START NEXT"):
                        st.session_state.messages = []
                        st.session_state.display_messages = [] # Temizle
                        st.session_state.reading_phase = False
                        st.session_state.reading_completed = False
                        st.session_state.final_report = None
                        st.session_state.accumulated_speaking_time = 0
                        st.rerun()
else:
    st.warning("Enter API Key")
