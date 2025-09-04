# New module: pure game logic (no rendering)
import random
from constants import (PROPERTIES, PROPERTY_SPACE_INDICES, RAILROADS, UTILITIES,
                       COMMUNITY_CHEST_CARDS, CHANCE_CARDS,
                       RAILROADS as RAILROAD_CONSTS, UTILITIES as UTILITY_CONSTS,
                       STARTING_MONEY, PLAYER_COLORS)
from player import Player

RAILROAD_SPACES = [5, 15, 25, 35]
UTILITY_SPACES = [12, 28]
COMMUNITY_CHEST_SPACES = [2, 17, 33]
CHANCE_SPACES = [7, 22, 36]
INCOME_TAX_SPACE = 4
LUXURY_TAX_SPACE = 38
GO_SPACE = 0

def new_shuffled_deck(cards):
    deck = list(cards)
    random.shuffle(deck)
    return deck

def draw_from_deck(deck):
    if not deck:
        return None
    card = deck.pop(0)
    deck.append(card)
    return card

def initialize_players(num_players, player_factory=Player):
    players = [player_factory(f"Player {i+1}") for i in range(num_players)]
    for i, p in enumerate(players):
        p.position = 0
        p.jail_free_cards = getattr(p, "jail_free_cards", 0)
        p.consecutive_doubles = 0
        p.has_rolled = False
        p.money = getattr(p, "money", STARTING_MONEY)
        # assign a visible color from constants so UI renders colored panels and tokens
        p.color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
    return players

def handle_player_landing(player, players, dice_sum=None, community_deck=None, chance_deck=None):
    """
    Pure game-state logic. Returns (success: bool, result: dict or None).
    Result structure matches the previous monopoly.py conventions.
    """
    # Income tax
    if player.position == INCOME_TAX_SPACE:
        tax = 200
        if player.money < tax:
            return False, {"type":"error", "message": f"{player.name} can't afford Income Tax (${tax})!"}
        player.money -= tax
        return True, {"space": player.position, "paid": tax, "type": "tax", "name": "Income Tax"}

    # Luxury tax
    if player.position == LUXURY_TAX_SPACE:
        tax = 100
        if player.money < tax:
            return False, {"type":"error", "message": f"{player.name} can't afford Luxury Tax (${tax})!"}
        player.money -= tax
        return True, {"space": player.position, "paid": tax, "type": "tax", "name": "Luxury Tax"}

    # Community Chest
    if player.position in COMMUNITY_CHEST_SPACES:
        card = draw_from_deck(community_deck) if community_deck is not None else random.choice(COMMUNITY_CHEST_CARDS)
        action = card.get("action")
        if action:
            typ = action[0]
            if typ == "money":
                amt = action[1]
                if amt < 0 and player.money < -amt:
                    return False, {"type":"error", "message": f"{player.name} can't afford Community Chest payment ${-amt}!"}
                player.money += amt
                return True, {"type":"community","card":card}
            if typ == "jail_free":
                player.jail_free_cards = getattr(player, "jail_free_cards", 0) + action[1]
                return True, {"type":"community","card":card}
            if typ == "collect_from_each":
                amt = action[1]
                total = 0
                for p in players:
                    if p is not player:
                        if p.money < amt:
                            return False, {"type":"error", "message": f"{p.name} can't afford ${amt}!"}
                        p.money -= amt
                        total += amt
                player.money += total
                return True, {"type":"community","card":card, "paid": total}
            if typ == "go_to_jail":
                player.position = 10
                return True, {"type":"community","card":card, "post": {"go_to":"jail"}}
            if typ == "advance":
                _, target_idx, collect_if = action
                # Interpret the numeric target:
                #  - If it explicitly references a railroad/utility board-space, use it directly.
                #  - Else if it's a small int that maps to a property list index, map via PROPERTY_SPACE_INDICES.
                #  - Else if it's a 0..39 board index, use directly.
                target_space = None
                if isinstance(target_idx, int):
                    if target_idx in RAILROAD_SPACES or target_idx in UTILITY_SPACES:
                        target_space = target_idx
                    elif 0 <= target_idx < len(PROPERTIES):
                        # treat as property-list index -> map to board space
                        target_space = PROPERTY_SPACE_INDICES[target_idx]
                    elif 0 <= target_idx < 40:
                        target_space = target_idx
                if target_space is None:
                    # fallback
                    target_space = target_idx
                if player.position > target_space and collect_if:
                    player.money += 200
                player.position = target_space
                # call landing logic for the new space and return its status/result
                post_success, post_result = handle_player_landing(player, players, dice_sum=None, community_deck=community_deck, chance_deck=chance_deck)
                return post_success, {"type":"community","card":card, "post_result": post_result}
            if typ == "pay_per_house_hotel":
                house_cost, hotel_cost = action[1]
                houses = 0; hotels = 0
                for prop in player.properties:
                    h = prop.get("houses",0)
                    if h >= 5:
                        hotels += 1
                    else:
                        houses += h
                total = houses * house_cost + hotels * hotel_cost
                if player.money < total:
                    return False, {"type":"error", "message": f"{player.name} can't afford repairs ${total}!"}
                player.money -= total
                return True, {"type":"community","card":card, "paid": total}
        return True, {"type":"community","card":card}

    # Chance
    if player.position in CHANCE_SPACES:
        card = draw_from_deck(chance_deck) if chance_deck is not None else random.choice(CHANCE_CARDS)
        action = card.get("action")
        if action:
            typ = action[0]
            if typ == "money":
                amt = action[1]
                if amt < 0 and player.money < -amt:
                    return False, {"type":"error", "message": f"{player.name} can't afford Chance payment ${-amt}!"}
                player.money += amt
                return True, {"type":"chance","card":card}
            if typ == "jail_free":
                player.jail_free_cards = getattr(player, "jail_free_cards", 0) + action[1]
                return True, {"type":"chance","card":card}
            if typ == "advance":
                _, target_idx, collect_if = action
                target_space = None
                if isinstance(target_idx, int):
                    if target_idx in RAILROAD_SPACES or target_idx in UTILITY_SPACES:
                        target_space = target_idx
                    elif 0 <= target_idx < len(PROPERTIES):
                        target_space = PROPERTY_SPACE_INDICES[target_idx]
                    elif 0 <= target_idx < 40:
                        target_space = target_idx
                if target_space is None:
                    target_space = target_idx
                if player.position > target_space and collect_if:
                    player.money += 200
                player.position = target_space
                post_success, post_result = handle_player_landing(player, players, dice_sum=None, community_deck=community_deck, chance_deck=chance_deck)
                return post_success, {"type":"chance","card":card, "post_result": post_result}
            if typ == "advance_nearest":
                kind = action[1]
                start = player.position
                chosen = None
                if kind == "railroad":
                    for offset in range(1,41):
                        idx = (start + offset) % 40
                        if idx in RAILROAD_SPACES:
                            chosen = idx; break
                else:
                    for offset in range(1,41):
                        idx = (start + offset) % 40
                        if idx in UTILITY_SPACES:
                            chosen = idx; break
                if chosen is not None:
                    player.position = chosen
                    # check ownership
                    owner = None
                    for p in players:
                        for owned in p.properties:
                            if owned.get("kind") == ("railroad" if kind=="railroad" else "utility") and owned.get("index") == (RAILROAD_SPACES.index(chosen) if kind=="railroad" else UTILITY_SPACES.index(chosen)):
                                owner = p; break
                        if owner: break
                    if owner and owner != player:
                        if kind == "utility":
                            d1 = random.randint(1,6); d2 = random.randint(1,6)
                            rent = (d1 + d2) * 10
                        else:
                            owned_count = sum(1 for o in owner.properties if o.get("kind")=="railroad")
                            rent = RAILROADS[0]["rent_steps"][min(max(0,owned_count-1), len(RAILROADS[0]["rent_steps"])-1)] * (2 if kind=="railroad" else 1)
                        if player.money < rent:
                            return False, {"type":"error", "message": f"{player.name} can't afford rent ${rent}!"}
                        player.money -= rent
                        owner.money += rent
                        return True, {"type":"chance","card":card, "paid": rent}
                    # unowned
                    if kind == "utility":
                        return True, {"type":"chance","card":card, "property": UTILITIES[UTILITY_SPACES.index(chosen)], "owner": None, "space": chosen}
                    else:
                        return True, {"type":"chance","card":card, "property": RAILROADS[RAILROAD_SPACES.index(chosen)], "owner": None, "space": chosen}
                return True, {"type":"chance","card":card}
            if typ == "advance_relative":
                rel = action[1]
                player.position = (player.position + rel) % 40
                post_success, post_result = handle_player_landing(player, players, dice_sum=None, community_deck=community_deck, chance_deck=chance_deck)
                return post_success, {"type":"chance","card":card, "post_result": post_result}
            if typ == "go_to_jail":
                player.position = 10
                return True, {"type":"chance","card":card, "post": {"go_to":"jail"}}
            if typ == "pay_per_house_hotel":
                house_cost, hotel_cost = action[1]
                houses = 0; hotels = 0
                for prop in player.properties:
                    h = prop.get("houses",0)
                    if h >= 5: hotels += 1
                    else: houses += h
                total = houses * house_cost + hotels * hotel_cost
                if player.money < total:
                    return False, {"type":"error", "message": f"{player.name} can't afford ${total}!"}
                player.money -= total
                return True, {"type":"chance","card":card, "paid": total}
            if typ == "pay_each_player":
                amt = action[1]
                if player.money < amt*(len(players)-1):
                    return False, {"type":"error", "message": f"{player.name} can't afford to pay each player ${amt}!"}
                for p in players:
                    if p is not player:
                        p.money += amt
                        player.money -= amt
                return True, {"type":"chance","card":card}
        return True, {"type":"chance","card":card}

    # Railroads
    if player.position in RAILROAD_SPACES:
        idx = RAILROAD_SPACES.index(player.position)
        owner = None; owner_entry = None
        for p in players:
            for owned in p.properties:
                if owned.get("kind")=="railroad" and owned.get("index")==idx:
                    owner = p; owner_entry = owned; break
            if owner: break
        if owner and owner != player:
            owned_count = sum(1 for o in owner.properties if o.get("kind")=="railroad")
            rent = RAILROADS[idx]["rent_steps"][min(max(0,owned_count-1), len(RAILROADS[idx]["rent_steps"])-1)]
            if player.money < rent:
                return False, {"type":"error", "message": f"{player.name} can't afford rent ${rent}!"}
            player.money -= rent; owner.money += rent
            return True, {"space": player.position, "property": RAILROADS[idx], "owner": owner, "paid": rent, "type":"railroad"}
        return True, {"space": player.position, "property": RAILROADS[idx], "owner": None, "paid": None, "type":"railroad"}

    # Utilities
    if player.position in UTILITY_SPACES:
        idx = UTILITY_SPACES.index(player.position)
        owner = None
        for p in players:
            for owned in p.properties:
                if owned.get("kind")=="utility" and owned.get("index")==idx:
                    owner = p; break
            if owner: break
        if owner and owner != player:
            owned_count = sum(1 for o in owner.properties if o.get("kind")=="utility")
            factor = 4 if owned_count==1 else 10
            rent = factor * (dice_sum or 0)
            if player.money < rent:
                return False, {"type":"error", "message": f"{player.name} can't afford utility rent ${rent}!"}
            player.money -= rent; owner.money += rent
            return True, {"space": player.position, "property": UTILITIES[idx], "owner": owner, "paid": rent, "type":"utility"}
        return True, {"space": player.position, "property": UTILITIES[idx], "owner": None, "paid": None, "type":"utility"}

    # Standard properties
    if player.position in PROPERTY_SPACE_INDICES:
        prop_idx = PROPERTY_SPACE_INDICES.index(player.position)
        prop = PROPERTIES[prop_idx]
        property_owner = None; owner_owned_entry = None
        for p in players:
            for owned in p.properties:
                if owned.get("kind")=="property" and owned.get("index")==prop_idx:
                    property_owner = p; owner_owned_entry = owned; break
            if property_owner: break
        if property_owner and property_owner != player:
            houses = owner_owned_entry.get("houses",0) if owner_owned_entry else 0
            houses = max(0, min(houses, len(prop.get("rents",[]))-1))
            rent = prop.get("rents",[0])[houses]
            if player.money < rent:
                return False, {"type":"error", "message": f"{player.name} can't afford rent ${rent}!"}
            player.money -= rent; property_owner.money += rent
            return True, {"property": prop, "owner": property_owner, "paid": rent, "space": player.position, "type":"property"}
        else:
            return True, {"property": prop, "owner": None, "paid": None, "space": player.position, "type":"property"}

    return True, None