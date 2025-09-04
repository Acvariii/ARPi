from constants import STARTING_MONEY, PROPERTIES, PROPERTY_SPACE_INDICES, RAILROADS, UTILITIES

class Player:
    """Represents a player in the game with properties, money, and game state"""

    def __init__(self, name, avatar=None):
        self.name = name
        self.avatar = avatar
        self.position = 0
        self.money = STARTING_MONEY
        self.properties = []  # list of owned property dicts with "index" and "houses"
        self.has_rolled = False
        self.color = None

    def move(self, steps):
        """Move player around the full 40-space board (clockwise starting at GO=0 in bottom-right)."""
        # wrap around 40 spaces (standard Monopoly board indexing)
        self.position = (self.position + steps) % 40
        return self.position

    def buy_property(self, property_index):
        """Attempt to purchase a property if player has enough money and it's not owned"""
        if property_index < len(PROPERTIES):
            property_data = PROPERTIES[property_index]
            if (self.money >= property_data["price"] and
                property_index not in [p["index"] for p in self.properties if p.get("kind") == "property"]):
                self.money -= property_data["price"]
                # store houses count on owned property
                owned = {"kind": "property", "index": property_index, "name": property_data["name"],
                         "price": property_data["price"], "price_per_house": property_data.get("price_per_house", 0),
                         "houses": 0, "group": property_data.get("group")}
                self.properties.append(owned)
                return True
        return False

    def buy_railroad(self, railroad_index):
        """Buy railroad by index in RAILROADS list (0..3)"""
        if 0 <= railroad_index < len(RAILROADS):
            data = RAILROADS[railroad_index]
            already = any(p.get("kind") == "railroad" and p.get("index") == railroad_index for p in self.properties)
            if not already and self.money >= data["price"]:
                self.money -= data["price"]
                owned = {"kind": "railroad", "index": railroad_index, "name": data["name"], "price": data["price"]}
                self.properties.append(owned)
                return True
        return False

    def buy_utility(self, utility_index):
        """Buy utility by index in UTILITIES list (0..1)"""
        if 0 <= utility_index < len(UTILITIES):
            data = UTILITIES[utility_index]
            already = any(p.get("kind") == "utility" and p.get("index") == utility_index for p in self.properties)
            if not already and self.money >= data["price"]:
                self.money -= data["price"]
                owned = {"kind": "utility", "index": utility_index, "name": data["name"], "price": data["price"]}
                self.properties.append(owned)
                return True
        return False

    def has_monopoly(self, property_index):
        """Return True if player owns the whole colour group of the property_index"""
        if property_index >= len(PROPERTIES):
            return False
        group = PROPERTIES[property_index].get("group")
        group_props = [i for i,p in enumerate(PROPERTIES) if p.get("group") == group]
        owned_indexes = {p["index"] for p in self.properties}
        return all(idx in owned_indexes for idx in group_props)

    def buy_house(self, property_index):
        """
        Buy a house for property_index if player owns full group and can afford it.
        Returns True if house bought.
        """
        if not self.has_monopoly(property_index):
            return False
        for prop in self.properties:
            if prop["index"] == property_index:
                price = prop.get("price_per_house", PROPERTIES[property_index].get("price_per_house", 0))
                if self.money >= price and prop.get("houses", 0) < 5:
                    self.money -= price
                    prop["houses"] = prop.get("houses", 0) + 1
                    return True
        return False

    def mortgage_property(self, property_index):
        """Simple mortgage: remove property, credit mortgage value (no unmortgage logic here)"""
        for prop in list(self.properties):
            if prop["index"] == property_index:
                # locate original data
                orig = PROPERTIES[property_index]
                self.money += orig.get("mortgage", 0)
                self.properties.remove(prop)
                return True
        return False

    def pay_rent(self, amount, owner):
        """Attempt to pay rent; if can't, return False"""
        if self.money >= amount:
            self.money -= amount
            owner.money += amount
            return True
        else:
            return False

    def can_buy_current_property(self, players):
        """Check if player can buy the property they're currently on (maps board pos -> property list)."""
        # Map board-space position into PROPERTIES list index if this is a property space
        if self.position not in PROPERTY_SPACE_INDICES:
            return False
        prop_idx = PROPERTY_SPACE_INDICES.index(self.position)
        for player in players:
            for prop in player.properties:
                if prop["index"] == prop_idx:
                    return False
        return self.money >= PROPERTIES[prop_idx]["price"]