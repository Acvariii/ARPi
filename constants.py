# Game constants
import pygame

# Colors
BACKGROUND = (25, 25, 35)
TEXT_COLOR = (240, 240, 240)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (90, 150, 200)

# Board original artwork/reference size
BOARD_ORIG_SIZE = (2000, 2000)
CORNER_SIZE = (262, 262)
EDGE_TILE_SIZE = {
    "top_bottom": (164, 262),   # width,height for top/bottom edge tiles in original art
    "left_right": (262, 164)    # width,height for left/right edge tiles in original art
}

# Starting money and player colours
STARTING_MONEY = 1500
PLAYER_COLORS = [
    (200,40,40), (40,120,200), (40,200,120), (200,180,40),
    (160,40,200), (200,80,140), (100,180,40), (40,40,180)
]

# Properties (houses/hotel rents included as rents[0..5] where rents[0] = base rent)
PROPERTIES = [
    {"name":"Mediterranean Avenue","price":60,  "price_per_house":50,  "rents":[2,10,30,90,160,250],  "mortgage":30,  "color":(149,84,54),   "group":"Brown"},
    {"name":"Baltic Avenue","price":60,         "price_per_house":50,  "rents":[4,20,60,180,320,450], "mortgage":30,  "color":(149,84,54),   "group":"Brown"},
    {"name":"Oriental Avenue","price":100,      "price_per_house":50,  "rents":[6,30,90,270,400,550], "mortgage":50,  "color":(170,224,250), "group":"Light Blue"},
    {"name":"Vermont Avenue","price":100,       "price_per_house":50,  "rents":[6,30,90,270,400,550], "mortgage":50,  "color":(170,224,250), "group":"Light Blue"},
    {"name":"Connecticut Avenue","price":120,   "price_per_house":50,  "rents":[8,40,100,300,450,600], "mortgage":60,  "color":(170,224,250), "group":"Light Blue"},
    {"name":"St. Charles Place","price":140,    "price_per_house":100, "rents":[10,50,150,450,625,750], "mortgage":70,  "color":(217,58,150),  "group":"Pink"},
    {"name":"States Avenue","price":140,        "price_per_house":100, "rents":[10,50,150,450,625,750], "mortgage":70,  "color":(217,58,150),  "group":"Pink"},
    {"name":"Virginia Avenue","price":160,      "price_per_house":100, "rents":[12,60,180,500,700,900], "mortgage":80,  "color":(217,58,150),  "group":"Pink"},
    {"name":"St. James Place","price":180,      "price_per_house":100, "rents":[14,70,200,550,750,950], "mortgage":90,  "color":(247,148,29),  "group":"Orange"},
    {"name":"Tennessee Avenue","price":180,     "price_per_house":100, "rents":[14,70,200,550,750,950], "mortgage":90,  "color":(247,148,29),  "group":"Orange"},
    {"name":"New York Avenue","price":200,      "price_per_house":100, "rents":[16,80,220,600,800,1000],"mortgage":100, "color":(247,148,29),  "group":"Orange"},
    {"name":"Kentucky Avenue","price":220,      "price_per_house":150, "rents":[18,90,250,700,875,1050],"mortgage":110, "color":(237,27,36),   "group":"Red"},
    {"name":"Indiana Avenue","price":220,       "price_per_house":150, "rents":[18,90,250,700,875,1050],"mortgage":110, "color":(237,27,36),   "group":"Red"},
    {"name":"Illinois Avenue","price":240,      "price_per_house":150, "rents":[20,100,300,750,925,1100],"mortgage":120, "color":(237,27,36),   "group":"Red"},
    {"name":"Atlantic Avenue","price":260,      "price_per_house":150, "rents":[22,110,330,800,975,1150],"mortgage":130, "color":(254,242,0),   "group":"Yellow"},
    {"name":"Ventnor Avenue","price":260,       "price_per_house":150, "rents":[22,110,330,800,975,1150],"mortgage":130, "color":(254,242,0),   "group":"Yellow"},
    {"name":"Marvin Gardens","price":280,       "price_per_house":150, "rents":[24,120,360,850,1025,1200],"mortgage":140, "color":(254,242,0),   "group":"Yellow"},
    {"name":"Pacific Avenue","price":300,       "price_per_house":200, "rents":[26,130,390,900,1100,1275],"mortgage":150, "color":(31,178,90),   "group":"Green"},
    {"name":"North Carolina Avenue","price":300,"price_per_house":200, "rents":[26,130,390,900,1100,1275],"mortgage":150, "color":(31,178,90),   "group":"Green"},
    {"name":"Pennsylvania Avenue","price":320,  "price_per_house":200, "rents":[28,150,450,1000,1200,1400],"mortgage":160, "color":(31,178,90),   "group":"Green"},
    {"name":"Park Place","price":350,           "price_per_house":200, "rents":[35,175,500,1100,1300,1500],"mortgage":175, "color":(0,114,187),    "group":"Dark Blue"},
    {"name":"Boardwalk","price":400,            "price_per_house":200, "rents":[50,200,600,1400,1700,2000],"mortgage":200, "color":(0,114,187),    "group":"Dark Blue"},
]

# Railroads
RAILROADS = [
    {"name":"Reading Railroad", "price":200, "rent_steps":[25,50,100,200], "mortgage":100},
    {"name":"Pennsylvania Railroad", "price":200, "rent_steps":[25,50,100,200], "mortgage":100},
    {"name":"B. & O. Railroad", "price":200, "rent_steps":[25,50,100,200], "mortgage":100},
    {"name":"Short Line Railroad", "price":200, "rent_steps":[25,50,100,200], "mortgage":100},
]

# Utilities
UTILITIES = [
    {"name":"Electric Company", "price":150, "mortgage":75},
    {"name":"Water Works", "price":150, "mortgage":75},
]

# Community Chest cards (full list)
COMMUNITY_CHEST_CARDS = [
    {"id": "cc_collect_100", "text": "You set aside time every week to hang out with your elderly neighbor – you’ve heard some amazing stories! COLLECT $100.", "action": ("money", 100)},
    {"id": "cc_collect_50",  "text": "You organize a group to clean up your town’s footpaths. COLLECT $50.", "action": ("money", 50)},
    {"id": "cc_collect_10",  "text": "You volunteered at a blood donation. There were free cookies! COLLECT $10.", "action": ("money", 10)},
    {"id": "cc_pay_50",      "text": "You buy a few bags of cookies from that school bake sale. Yum! PAY $50.", "action": ("money", -50)},
    {"id": "cc_getout",      "text": "GET OUT OF JAIL FREE. Keep this card until needed.", "action": ("jail_free", 1)},
    {"id": "cc_collect_from_each_10", "text": "You organize a street party... COLLECT $10 FROM EACH PLAYER.", "action": ("collect_from_each", 10)},
    {"id": "cc_go_to_jail",  "text": "GO TO JAIL. DO NOT PASS GO.", "action": ("go_to_jail", None)},
    {"id": "cc_collect_20",  "text": "You help your neighbor bring in her groceries. COLLECT $20.", "action": ("money", 20)},
    {"id": "cc_collect_100_b","text": "You help build a new school playground – COLLECT $100.", "action": ("money", 100)},
    {"id": "cc_collect_100_c","text": "You spend the day playing games with kids at a local children’s hospital. COLLECT $100.", "action": ("money", 100)},
    {"id": "cc_pay_100",     "text": "You go to the local school’s car wash fundraiser – PAY $100.", "action": ("money", -100)},
    {"id": "cc_advance_go",  "text": "ADVANCE TO GO. (COLLECT $200)", "action": ("advance", 0, True)},
    {"id": "cc_collect_200", "text": "You help your neighbors clean up after a storm. COLLECT $200.", "action": ("money", 200)},
    {"id": "cc_pay_50_b",    "text": "Donation to animal shelter. PAY $50.", "action": ("money", -50)},
    {"id": "cc_pay_for_repairs", "text": "For each house pay $40. For each hotel pay $115.", "action": ("pay_per_house_hotel", (40, 115))},
    {"id": "cc_collect_25",  "text": "You organize a bake sale. COLLECT $25.", "action": ("money", 25)}
]

# Chance cards (full list)
CHANCE_CARDS = [
    {"id": "ch_boardwalk", "text": "Advance to Boardwalk.", "action": ("advance", len(PROPERTIES)-1, False)},
    {"id": "ch_go",        "text": "Advance to Go (Collect $200).", "action": ("advance", 0, True)},
    {"id": "ch_illinois",  "text": "Advance to Illinois Avenue. If you pass Go, collect $200.", "action": ("advance", 12, True)},
    {"id": "ch_st_charles","text": "Advance to St. Charles Place. If you pass Go, collect $200.", "action": ("advance", 5, True)},
    {"id": "ch_nearest_rail","text": "Advance to the nearest Railroad.", "action": ("advance_nearest", "railroad")},
    {"id": "ch_nearest_rail_b","text": "Advance to the nearest Railroad.", "action": ("advance_nearest", "railroad")},
    {"id": "ch_nearest_utility","text": "Advance token to nearest Utility.", "action": ("advance_nearest", "utility")},
    {"id": "ch_dividend",  "text": "Bank pays you dividend of $50.", "action": ("money", 50)},
    {"id": "ch_getout",    "text": "Get Out of Jail Free.", "action": ("jail_free", 1)},
    {"id": "ch_back_3",    "text": "Go Back 3 Spaces.", "action": ("advance_relative", -3)},
    {"id": "ch_go_to_jail","text": "Go to Jail. Do not pass Go.", "action": ("go_to_jail", None)},
    {"id": "ch_repairs",   "text": "For each house pay $25. For each hotel pay $100.", "action": ("pay_per_house_hotel", (25, 100))},
    {"id": "ch_speeding",  "text": "Speeding fine $15.", "action": ("money", -15)},
    {"id": "ch_reading",   "text": "Advance to Reading Railroad.", "action": ("advance", 5, True)},
    {"id": "ch_chairman",  "text": "Pay each player $50.", "action": ("pay_each_player", 50)},
    {"id": "ch_loan",      "text": "Collect $150.", "action": ("money", 150)}
]

# Fonts - will be initialized later
FONT_LARGE = None
FONT_MEDIUM = None
FONT_SMALL = None
FONT_ACTION = None

def init_fonts():
    global FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_ACTION
    FONT_LARGE = pygame.font.SysFont("Arial", 48, bold=True)
    FONT_MEDIUM = pygame.font.SysFont("Arial", 36)
    FONT_SMALL = pygame.font.SysFont("Arial", 22)
    FONT_ACTION = pygame.font.SysFont("Arial", 16)

# Game data
GAMES = [
    {"name": "Monopoly", "image_path": "monopoly.jpg", "max_players": 8, "board_shape": "square"},
    {"name": "Risk", "image_path": "risk.png", "max_players": 6, "board_shape": "rectangle"}
]

PROPERTY_SPACE_INDICES = [
    1, 3, 6, 8, 9, 11, 13, 14, 16, 18, 19, 21, 23, 24, 26, 27, 29, 31, 32, 34, 37, 39
]

CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
CAPTURE_ASPECT = CAPTURE_WIDTH / max(1, CAPTURE_HEIGHT)