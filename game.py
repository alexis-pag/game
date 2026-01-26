import pygame
import random
import math
import json
import os
from enum import Enum

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 700
MAP_WIDTH, MAP_HEIGHT = 2400, 1400
FPS = 60

BLACK = (0, 0, 0)
PURPLE = (138, 43, 226)
DARK_PURPLE = (75, 0, 130)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (100, 149, 237)
GRAY = (128, 128, 128)
DARK_GRAY = (50, 50, 50)
GOLD = (255, 215, 0)

class GameState(Enum):
    MAIN_MENU = 0
    START_MENU = 1
    PLAYING = 2
    GAME_OVER = 3
    VICTORY = 4
    PAUSED = 5
    SHOP = 6
    SETTINGS = 7
    CHARACTER_SELECT = 8
    QUEST_MENU = 9

class Item:
    def __init__(self, name, item_type, level, price, damage=0, hp_bonus=0, description=""):
        self.name = name
        self.type = item_type
        self.level = level
        self.price = price
        self.damage = damage
        self.hp_bonus = hp_bonus
        self.description = description
        self.owned = False
        self.equipped = False
    
    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'level': self.level,
            'owned': self.owned,
            'equipped': self.equipped
        }
    
    @staticmethod
    def from_dict(data, items_catalog):
        for item in items_catalog:
            if item.name == data['name']:
                item.owned = data['owned']
                item.equipped = data['equipped']
                return item
        return None

class SaveManager:
    def __init__(self):
        self.save_file = "game_meta_save.json"

    def save_meta_progression(self, currency, items, unlocked_classes, quest_progress, mastery_unlocks=None, last_class=None):
        """Save ONLY meta progression data - never runtime state"""
        if mastery_unlocks is None:
            mastery_unlocks = []
        
        owned_items = []
        for item in items:
            if item.owned:
                owned_items.append({
                    'name': item.name,
                    'type': item.type,
                    'level': item.level,
                    'equipped': item.equipped
                })

        highest_armor = 0
        highest_weapon = 0
        default_armor = None
        default_weapon = None

        for item_data in owned_items:
            if item_data['type'] == 'armor':
                highest_armor = max(highest_armor, item_data['level'])
                if item_data['equipped']:
                    default_armor = item_data['name']
            elif item_data['type'] in ['sword', 'weapon']:
                highest_weapon = max(highest_weapon, item_data['level'])
                if item_data['equipped']:
                    default_weapon = item_data['name']

        meta_data = {
            'total_credits': currency,
            'owned_items': owned_items,
            'highest_armor_tier': highest_armor,
            'highest_weapon_tier': highest_weapon,
            'default_armor': default_armor,
            'default_weapon': default_weapon,
            'unlocked_classes': list(unlocked_classes),
            'mastery_unlocks': list(mastery_unlocks),
            'quest_progress': quest_progress,
            'last_selected_class': last_class,
            # Meta unlocks
            'unlocked_boss_phases': []
        }

        try:
            with open(self.save_file, 'w') as f:
                json.dump(meta_data, f, indent=4)
            return True
        except Exception as e:
            print(f"Meta save error: {e}")
            return False
    
    def load_meta_progression(self, items_catalog):
        """Load ONLY meta progression data - never runtime state"""
        if not os.path.exists(self.save_file):
            return None

        try:
            with open(self.save_file, 'r') as f:
                meta_data = json.load(f)

            # Restore item ownership and equipped status
            for item_data in meta_data['owned_items']:
                for item in items_catalog:
                    if item.name == item_data['name']:
                        item.owned = True
                        item.equipped = item_data['equipped']
                        break

            # Restore unlocked classes and masteries
            unlocked_classes = set(meta_data.get('unlocked_classes', []))
            mastery_unlocks = set(meta_data.get('mastery_unlocks', []))

            return meta_data, unlocked_classes, mastery_unlocks
        except Exception as e:
            print(f"Meta load error: {e}")
            return None, set(), set()
    
    def save_exists(self):
        return os.path.exists(self.save_file)
    
    def delete_save(self):
        """Delete the save file - used for complete reset"""
        try:
            if os.path.exists(self.save_file):
                os.remove(self.save_file)
            return True
        except Exception as e:
            print(f"Delete save error: {e}")
            return False

class Shop:
    def __init__(self):
        self.items = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.max_visible = 5
        
        # Initialize shop items
        self.init_items()
    
    def init_items(self):
        # Armors (5 levels)
        armor_hp = [50, 100, 200, 350, 500]
        armor_prices = [100, 300, 600, 1200, 2500]
        for i in range(5):
            self.items.append(Item(
                f"Armor Lv{i+1}",
                "armor",
                i+1,
                armor_prices[i],
                hp_bonus=armor_hp[i],
                description=f"Max HP: {armor_hp[i]}"
            ))
        
        # Swords (5 levels)
        sword_dmg = [2, 5, 10, 15, 20]
        sword_prices = [150, 400, 800, 1500, 3000]
        for i in range(5):
            self.items.append(Item(
                f"Sword Lv{i+1}",
                "sword",
                i+1,
                sword_prices[i],
                damage=sword_dmg[i],
                description=f"Damage: {sword_dmg[i]}"
            ))
        
        # Crossbow
        self.items.append(Item(
            "Crossbow",
            "weapon",
            1,
            2000,
            damage=5,
            description="Charge: 5-25 dmg, Long range, Slow charge"
        ))
        
        # Sniper
        self.items.append(Item(
            "Sniper",
            "weapon",
            1,
            5000,
            damage=20,
            description="Charge: 20-70 dmg, Map range, No movement"
        ))
    
    def buy_item(self, currency):
        item = self.items[self.selected_index]
        if item.owned:
            return currency, "Already owned"
        
        if currency >= item.price:
            item.owned = True
            if item.type == "armor":
                # Unequip other armors
                for i in self.items:
                    if i.type == "armor" and i.equipped:
                        i.equipped = False
                item.equipped = True
            elif item.type in ["sword", "weapon"]:
                # Unequip other weapons
                for i in self.items:
                    if i.type in ["sword", "weapon"] and i.equipped:
                        i.equipped = False
                item.equipped = True
            return currency - item.price, "Purchased!"
        return currency, "Not enough currency"
    
    def equip_item(self):
        item = self.items[self.selected_index]
        if not item.owned:
            return "Not owned"
        
        if item.type == "armor":
            for i in self.items:
                if i.type == "armor":
                    i.equipped = False
            item.equipped = True
            return "Armor equipped"
        elif item.type in ["sword", "weapon"]:
            for i in self.items:
                if i.type in ["sword", "weapon"]:
                    i.equipped = False
            item.equipped = True
            return "Weapon equipped"
        return ""
    
    def navigate(self, direction):
        self.selected_index = max(0, min(len(self.items) - 1, self.selected_index + direction))
        
        # Adjust scroll
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.selected_index - self.max_visible + 1
    
    def get_equipped_stats(self):
        hp_bonus = 200  # Base HP
        damage = 2  # Base damage
        weapon_type = "basic"
        
        for item in self.items:
            if item.equipped:
                if item.type == "armor":
                    hp_bonus = item.hp_bonus
                elif item.type == "sword":
                    damage = item.damage
                    weapon_type = "sword"
                elif item.name == "Crossbow":
                    weapon_type = "crossbow"
                elif item.name == "Sniper":
                    weapon_type = "sniper"
        
        return hp_bonus, damage, weapon_type

class Menu:
    def __init__(self):
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)
        self.font_tiny = pygame.font.Font(None, 24)
        
        self.main_options = ["Start Game", "Shop", "Quests", "Settings", "Exit (F5)"]  # ADDED "Quests"
        self.pause_options = ["Return to Menu (Run Lost)", "Quit Game (F5)"]  # CHANGED pause options
        self.settings_options = ["Volume: 50%", "Speed: Normal", "Back"]
        self.character_options = ["Warrior", "Mage", "Archer", "Rogue", "Reaver"]
        
        self.character_stats = {
            "Base": {
                "base_hp": 100,
                "passives": [],
                "active_buffs": [],
                "hp_bonus": 0
            },
            "Warrior": {
                "base_hp": 120,
                "passives": ["Resilient: +10 Max HP", "Counter Strike: 20% melee damage to attacker after parry"],
                "active_buffs": ["Shield Stance: -15% damage for 8s", "Berserk: +20% melee damage for 5s after parry"],
                "hp_bonus": 10
            },
            "Mage": {
                "base_hp": 90,
                "passives": ["Mana Affinity: 5% mana regen/s", "Spell Mastery: +15% magic damage on DoT targets"],
                "active_buffs": ["Arcane Surge: +20% cast speed for 6s", "Elemental Shield: -25% magic damage received for 5s"],
                "hp_bonus": 0
            },
            "Archer": {
                "base_hp": 95,
                "passives": ["Critical Eye: +10% crit chance", "Marksmanship: +15% ranged damage on immobilized targets"],
                "active_buffs": ["Focus Shot: +40% next attack damage", "Evasive Roll: Complete dodge for 0.8s"],
                "hp_bonus": 0
            },
            "Rogue": {
                "base_hp": 90,
                "passives": ["Agility: +10% move speed", "Critical Timing: +15% damage on consecutive attacks (2s)"],
                "active_buffs": ["Shadow Dash: Immunity to CC for 1s", "Backstab: +25% damage from behind"],
                "hp_bonus": 0
            },
            "Reaver": {
                "base_hp": 100,
                "passives": ["Life Stealer: +5% HP recovered per attack", "Survivor's Instinct: Below 20 HP, +25% regen for 4s"],
                "active_buffs": ["Siphon Strike: Heal 25% damage dealt for 5s", "Crimson Aura: 5 HP/s regen while enemies nearby"],
                "hp_bonus": 0
            }
        }
        
        self.selected = 0
        self.volume = 50
        self.game_speed = 1.0
        
        self.notification = ""
        self.notification_timer = 0
        
        # Quest menu state
        self.quest_view_state = 0  # 0: Class selection, 1: Quest list
        self.selected_quest_class = None
    
    def navigate(self, direction, current_state):
        if current_state == GameState.MAIN_MENU:
            options = self.main_options
        elif current_state == GameState.PAUSED:
            options = self.pause_options
        elif current_state == GameState.SETTINGS:
            options = self.settings_options
        elif current_state == GameState.CHARACTER_SELECT:
            options = self.character_options
        else:
            return
        
        self.selected = (self.selected + direction) % len(options)
    
    def show_notification(self, message):
        self.notification = message
        self.notification_timer = 180
    
    def update_notification(self):
        if self.notification_timer > 0:
            self.notification_timer -= 1
    
    def draw_main_menu(self, screen):
        screen.fill(BLACK)
        
        title = self.font_large.render("HOLLOW KNIGHT BOSS FIGHT", True, PURPLE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        
        y = 300
        for i, option in enumerate(self.main_options):
            color = YELLOW if i == self.selected else WHITE
            text = self.font_medium.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 70
        
        hint = self.font_tiny.render("Navigate: Arrow Keys | Select: Enter | F2: Admin Panel", True, GRAY)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))
        
        if self.notification_timer > 0:
            notif = self.font_small.render(self.notification, True, GREEN)
            screen.blit(notif, (SCREEN_WIDTH // 2 - notif.get_width() // 2, 220))
    
    def draw_pause_menu(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        title = self.font_large.render("PAUSED", True, PURPLE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 150))
        
        warning = self.font_small.render("WARNING: Returning to menu will END this run!", True, RED)
        screen.blit(warning, (SCREEN_WIDTH // 2 - warning.get_width() // 2, 250))
        
        y = 350
        for i, option in enumerate(self.pause_options):
            color = YELLOW if i == self.selected else WHITE
            text = self.font_medium.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 70
    
    def draw_settings(self, screen):
        screen.fill(BLACK)
        
        title = self.font_large.render("SETTINGS", True, PURPLE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        
        y = 300
        for i, option in enumerate(self.settings_options):
            color = YELLOW if i == self.selected else WHITE
            text = self.font_medium.render(option, True, color)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 70
        
        hint = self.font_tiny.render("Left/Right: Adjust | Enter: Select", True, GRAY)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))
    
    def draw_character_selection(self, screen, unlocked_classes):
        screen.fill(BLACK)

        title = self.font_large.render("SELECT YOUR CLASS", True, PURPLE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        # Filter available classes
        available_classes = ["Base"] + [cls for cls in self.character_options if cls in unlocked_classes]

        # Draw class options on the left
        y = 150
        for i, option in enumerate(available_classes):
            color = YELLOW if i == self.selected else WHITE
            text = self.font_medium.render(option, True, color)
            screen.blit(text, (100, y))
            y += 60

        # Draw selected class details on the right
        selected_class = available_classes[self.selected] if self.selected < len(available_classes) else "Base"
        stats = self.character_stats[selected_class]

        detail_x = SCREEN_WIDTH // 2
        pygame.draw.rect(screen, DARK_GRAY, (detail_x - 20, 140, 550, 450))
        pygame.draw.rect(screen, PURPLE, (detail_x - 20, 140, 550, 450), 2)

        class_title = self.font_large.render(selected_class.upper(), True, YELLOW)
        screen.blit(class_title, (detail_x, 150))

        hp_text = self.font_medium.render(f"Base HP: {stats['base_hp']}", True, RED)
        screen.blit(hp_text, (detail_x, 220))

        # Passives
        passives_label = self.font_small.render("PASSIVES:", True, BLUE)
        screen.blit(passives_label, (detail_x, 280))
        y_p = 310
        for passive in stats['passives']:
            p_text = self.font_tiny.render(f"• {passive}", True, WHITE)
            screen.blit(p_text, (detail_x + 20, y_p))
            y_p += 25

        # Active Buffs
        buffs_label = self.font_small.render("ACTIVE BUFFS:", True, GREEN)
        screen.blit(buffs_label, (detail_x, 380))
        y_b = 410
        for buff in stats['active_buffs']:
            b_text = self.font_tiny.render(f"• {buff}", True, WHITE)
            screen.blit(b_text, (detail_x + 20, y_b))
            y_b += 25

        hint = self.font_tiny.render("Navigate: Arrow Keys | Select: Enter | Back: ESC", True, GRAY)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def draw_quest_menu(self, screen, quests, quest_progress, unlocked_classes, mastery_unlocks=None):
        screen.fill(BLACK)
        if mastery_unlocks is None:
            mastery_unlocks = set()

        title = self.font_large.render("QUEST LOG", True, PURPLE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        if self.quest_view_state == 0:
            # Class selection
            subtitle = self.font_medium.render("Select a Class to View Quests", True, YELLOW)
            screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 120))
            
            all_quest_classes = ["Warrior", "Mage", "Archer", "Rogue", "Reaver"]
            y = 200
            for i, cls in enumerate(all_quest_classes):
                is_selected = i == self.selected
                is_unlocked = cls in unlocked_classes
                
                if is_selected:
                    color = YELLOW
                elif is_unlocked:
                    color = WHITE
                else:
                    color = GRAY
                
                display_text = cls
                if cls in mastery_unlocks:
                    display_text += " [MASTERED]"
                    if not is_selected: color = GOLD
                elif not is_unlocked:
                    display_text += " [LOCKED]"
                
                text = self.font_medium.render(display_text, True, color)
                screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
                y += 60
        else:
            # Quest list for selected class
            subtitle = self.font_medium.render(f"{self.selected_quest_class} Quests", True, YELLOW)
            screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 120))
            
            class_quests = {k: v for k, v in quests.items() if v['class'] == self.selected_quest_class}
            
            y = 200
            if not class_quests:
                msg = self.font_small.render("No quests available for this class.", True, GRAY)
                screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, y))
            else:
                for quest_key, quest in class_quests.items():
                    # Background for each quest
                    pygame.draw.rect(screen, DARK_GRAY, (80, y - 10, SCREEN_WIDTH - 160, 100))
                    pygame.draw.rect(screen, PURPLE, (80, y - 10, SCREEN_WIDTH - 160, 100), 1)

                    # Quest name
                    name_text = self.font_medium.render(quest['name'], True, WHITE)
                    screen.blit(name_text, (100, y))

                    # Progress
                    current_progress = quest_progress.get(quest_key, 0)
                    max_progress = quest['max_progress']
                    percent = min(100, int((current_progress / max_progress) * 100))
                    progress_text = self.font_small.render(f"Progress: {current_progress}/{max_progress} ({percent}%)", True, GRAY)
                    screen.blit(progress_text, (100, y + 40))

                    # Status
                    if current_progress >= max_progress:
                        status_text = self.font_small.render("COMPLETED", True, GREEN)
                    else:
                        status_text = self.font_small.render("IN PROGRESS", True, YELLOW)
                    screen.blit(status_text, (SCREEN_WIDTH - status_text.get_width() - 100, y + 20))

                    # Description
                    desc_text = self.font_tiny.render(quest['description'], True, GRAY)
                    screen.blit(desc_text, (100, y + 70))

                    y += 120

        if self.quest_view_state == 1:
            hint_text = "ESC/X/BACKSPACE: Back to Classes"
        else:
            hint_text = "ESC/X: Close Menu | ENTER: View Quests"
            
        hint = self.font_tiny.render(hint_text, True, GRAY)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def draw_shop(self, screen, shop, currency):
        screen.fill(BLACK)
        
        title = self.font_large.render("SHOP", True, PURPLE)
        screen.blit(title, (50, 30))
        
        currency_text = self.font_medium.render(f"Currency: {currency}", True, YELLOW)
        screen.blit(currency_text, (SCREEN_WIDTH - currency_text.get_width() - 50, 40))
        
        # Items list
        y = 150
        visible_items = shop.items[shop.scroll_offset:shop.scroll_offset + shop.max_visible]
        
        for i, item in enumerate(visible_items):
            actual_index = shop.scroll_offset + i
            is_selected = actual_index == shop.selected_index
            
            # Background
            bg_color = DARK_PURPLE if is_selected else DARK_GRAY
            pygame.draw.rect(screen, bg_color, (50, y, SCREEN_WIDTH - 100, 80))
            pygame.draw.rect(screen, PURPLE if is_selected else GRAY, (50, y, SCREEN_WIDTH - 100, 80), 2)
            
            # Item info
            name_text = self.font_medium.render(item.name, True, WHITE)
            screen.blit(name_text, (70, y + 10))
            
            desc_text = self.font_small.render(item.description, True, GRAY)
            screen.blit(desc_text, (70, y + 45))
            
            # Price
            price_color = GREEN if currency >= item.price or item.owned else RED
            price_text = self.font_small.render(f"${item.price}", True, price_color)
            screen.blit(price_text, (SCREEN_WIDTH - 250, y + 15))
            
            # Status
            if item.equipped:
                status = self.font_small.render("EQUIPPED", True, YELLOW)
                screen.blit(status, (SCREEN_WIDTH - 250, y + 45))
            elif item.owned:
                status = self.font_small.render("OWNED", True, GREEN)
                screen.blit(status, (SCREEN_WIDTH - 250, y + 45))
            
            y += 90
        
        # Controls
        controls = self.font_tiny.render("Up/Down: Navigate | B: Buy | E: Equip | ESC: Back", True, GRAY)
        screen.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, SCREEN_HEIGHT - 50))
        
        # Notification
        if self.notification_timer > 0:
            notif = self.font_small.render(self.notification, True, GREEN)
            screen.blit(notif, (SCREEN_WIDTH // 2 - notif.get_width() // 2, 100))

class Player:
    def __init__(self, max_hp=200, base_damage=2, weapon_type="basic"):
        self.width, self.height = 40, 60
        self.x, self.y = 400, 800
        self.vel_x, self.vel_y = 0, 0
        self.max_hp, self.hp = max_hp, max_hp
        self.base_damage = base_damage
        self.weapon_type = weapon_type
        self.speed, self.jump_power, self.gravity = 6, 15, 0.6
        self.jumps_left = 2
        self.on_ground = False
        self.on_wall = False
        self.wall_side = 0
        self.was_jumping = False
        
        self.dash_speed, self.dash_duration = 20, 10
        self.dash_cooldown_max, self.dash_cooldown = 30, 0
        self.dashing, self.dash_timer = False, 0
        self.dash_direction = 1
        self.invulnerable = False
        
        self.attack_cooldown_max, self.attack_cooldown = 180, 0
        
        self.charging = False
        self.charge_percent = 0
        self.max_charge = 200
        self.charge_rate = 25 / 60
        self.aim_angle = 0
        
        # Weapon-specific
        if weapon_type == "crossbow":
            self.charge_rate = 12.5 / 60  # 200% slower
        elif weapon_type == "sniper":
            self.aiming_sniper = False
        
        self.parrying = False
        self.fire_slow = False
        self.external_slow = 1.0
        self.burn_damage_timer = 0
        
        # Animation state
        self.visual_x = self.x
        self.visual_y = self.y
        self.facing_right = True
        self.animation_timer = 0
        self.squash_stretch = 1.0  # For jump/land animations
        self.dash_trail = []  # Trail effect for dash
        
        # Character Class specific
        self.character_class = None
        self.mana = 100
        self.max_mana = 100
        self.mana_regen = 0
        self.crit_chance = 0.05
        self.move_speed_bonus = 1.0
        self.consecutive_attacks = 0
        self.consecutive_attack_timer = 0

        # Quest progress tracking
        self.quest_progress = {
            'warrior_damage': 0,
            'mage_crystals': 0,
            'archer_range_damage': 0,
            'rogue_laser_avoids': 0,
            'reaver_low_hp_damage': 0,
            'warrior_parries': 0,
            'mage_mana_spent': 0,
            'archer_crit_hits': 0,
            'rogue_backstabs': 0,
            'reaver_hp_siphoned': 0
        }
        self.laser_damage_taken = False
        self.consecutive_laser_avoids = 0
        
        # Buff timers (in frames)
        self.buffs = {
            "shield_stance": 0,
            "berserk": 0,
            "arcane_surge": 0,
            "elemental_shield": 0,
            "focus_shot": False,
            "evasive_roll": 0,
            "shadow_dash": 0,
            "siphon_strike": 0,
            "crimson_aura": 0
        }
        self.buff_cooldowns = {
            "buff1": 0,
            "buff2": 0
        }
        self.buff_cooldowns_max = {
            "Warrior": {"buff1": 1200, "buff2": 0}, # 20s, Berserk is auto
            "Mage": {"buff1": 900, "buff2": 900}, # 15s
            "Archer": {"buff1": 600, "buff2": 300}, # 10s, 5s
            "Rogue": {"buff1": 480, "buff2": 0}, # 8s, Backstab is passive
            "Reaver": {"buff1": 1200, "buff2": 0} # 20s, Crimson is auto
        }
    
    def update(self, platforms, walls, temp_walls, fire_zones, mouse_pos, camera_x, camera_y, game_instance=None):
        keys = pygame.key.get_pressed()
        
        self.animation_timer += 1
        
        # Passive and Buff logic
        if self.character_class == "Mage":
            # Mana Affinity: 5% mana regen/s
            regen_amount = (self.max_mana * 0.05) / 60
            self.mana = min(self.max_mana, self.mana + regen_amount)
        elif self.character_class == "Rogue":
            # Agility: +10% move speed
            self.move_speed_bonus = 1.1
        elif self.character_class == "Reaver":
            # Survivor's Instinct: Below 20 HP, +25% regen for 4s (simulated as constant while low)
            if self.hp < 20:
                self.hp = min(self.max_hp, self.hp + (25 / 60 / 4)) # 25 HP over 4s
            # Crimson Aura: 5 HP/s regen while enemies nearby
            if self.buffs["crimson_aura"] > 0:
                self.hp = min(self.max_hp, self.hp + 5 / 60)
                self.buffs["crimson_aura"] -= 1

        # Rogue consecutive attacks
        if self.consecutive_attack_timer > 0:
            self.consecutive_attack_timer -= 1
        else:
            self.consecutive_attacks = 0

        # Decrement other buff timers
        for buff in self.buffs:
            if isinstance(self.buffs[buff], int) and self.buffs[buff] > 0:
                if buff != "crimson_aura": # Already handled above
                    self.buffs[buff] -= 1
        
        # Decrement cooldowns
        if self.buff_cooldowns["buff1"] > 0:
            self.buff_cooldowns["buff1"] -= 1
        if self.buff_cooldowns["buff2"] > 0:
            self.buff_cooldowns["buff2"] -= 1
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        if self.charging:
            charge_speed = self.charge_rate
            if self.buffs["arcane_surge"] > 0:
                charge_speed *= 1.2
            self.charge_percent = min(self.charge_percent + charge_speed, self.max_charge)
            world_mouse_x = mouse_pos[0] + camera_x
            world_mouse_y = mouse_pos[1] + camera_y
            dx = world_mouse_x - (self.x + self.width // 2)
            dy = world_mouse_y - (self.y + self.height // 2)
            self.aim_angle = math.atan2(dy, dx)
        
        if self.dashing:
            self.dash_timer -= 1
            self.vel_x = self.dash_speed * self.dash_direction
            self.vel_y = 0
            self.invulnerable = True
            
            # Dash trail effect
            self.dash_trail.append({'x': self.x, 'y': self.y, 'alpha': 150})
            if len(self.dash_trail) > 5:
                self.dash_trail.pop(0)
            
            if self.dash_timer <= 0:
                self.dashing = False
                self.invulnerable = False
                self.dash_trail.clear()
        else:
            # Fade out dash trail
            for trail in self.dash_trail:
                trail['alpha'] -= 30
            self.dash_trail = [t for t in self.dash_trail if t['alpha'] > 0]
            
            self.vel_x = 0
            speed = self.speed * self.external_slow * self.move_speed_bonus
            
            # Sniper cannot move while aiming
            if self.weapon_type == "sniper" and self.charging:
                speed = 0
            elif self.fire_slow:
                speed *= 0.5
            elif self.charging:
                speed *= 0.25 if self.charge_percent >= self.max_charge else 0.5
            
            # ZQSD controls (Q=left, D=right, S=fast fall)
            if keys[pygame.K_q]:
                self.vel_x = -speed
                self.facing_right = False
            if keys[pygame.K_d]:
                self.vel_x = speed
                self.facing_right = True
            if keys[pygame.K_s]:
                self.vel_y += self.gravity * 0.5  # Fast fall assistance
            
            if self.on_wall and self.vel_y > 0:
                self.vel_y += self.gravity * 0.3
            else:
                self.vel_y += self.gravity
        
        # Squash and stretch for jump/land
        if not self.on_ground and self.vel_y < 0:  # Jumping
            self.squash_stretch = 0.9
        elif not self.on_ground and self.vel_y > 5:  # Falling fast
            self.squash_stretch = 1.1
        else:  # On ground or normal
            self.squash_stretch += (1.0 - self.squash_stretch) * 0.2
        
        self.x += self.vel_x
        self.check_collision(platforms, walls, temp_walls, 'x')
        self.y += self.vel_y
        
        # Only check collision with platforms if they're visible, but floor always solid
        if game_instance is not None and hasattr(game_instance, 'platforms_visible'):
            if game_instance.platforms_visible:
                self.check_collision(platforms, walls, temp_walls, 'y')
            else:
                # Only check collision with ground platform when others invisible
                platforms_for_y = [platforms[0]] if platforms else []
                self.check_collision(platforms_for_y, walls, temp_walls, 'y')
        else:
            self.check_collision(platforms, walls, temp_walls, 'y')
        
        self.x = max(0, min(self.x, MAP_WIDTH - self.width))
        self.y = max(0, min(self.y, MAP_HEIGHT - self.height))
        
        # Smooth visual position
        self.visual_x += (self.x - self.visual_x) * 0.3
        self.visual_y += (self.y - self.visual_y) * 0.3
        
        self.fire_slow = False
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for fire in fire_zones:
            if player_rect.colliderect(fire['rect']):
                self.fire_slow = True
                if not self.dashing:
                    self.burn_damage_timer += 1
                    if self.burn_damage_timer >= 30:
                        self.take_damage(2, "fire")
                        self.burn_damage_timer = 0
        
        if not self.fire_slow:
            self.burn_damage_timer = 0
            
        self.external_slow = 1.0
    
    def check_collision(self, platforms, walls, temp_walls, axis):
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        all_walls = walls + [w['rect'] for w in temp_walls]
        
        if axis == 'y':
            self.on_ground = False
            self.on_wall = False
            for platform in platforms:
                if player_rect.colliderect(platform):
                    if self.vel_y > 0:
                        self.y = platform.top - self.height
                        self.vel_y = 0
                        self.on_ground = True
                        self.jumps_left = 2
                    elif self.vel_y < 0:
                        self.y = platform.bottom
                        self.vel_y = 0
            for wall in all_walls:
                if player_rect.colliderect(wall) and self.vel_y > 0:
                    self.y = wall.top - self.height
                    self.vel_y = 0
                    self.on_ground = True
                    self.jumps_left = 2
        elif axis == 'x':
            for platform in platforms:
                if player_rect.colliderect(platform):
                    if self.vel_x > 0:
                        self.x = platform.left - self.width
                        # Check if it's a vertical platform (narrow width)
                        if platform.width <= 30:
                            self.on_wall, self.wall_side, self.jumps_left = True, 1, 1
                    elif self.vel_x < 0:
                        self.x = platform.right
                        # Check if it's a vertical platform (narrow width)
                        if platform.width <= 30:
                            self.on_wall, self.wall_side, self.jumps_left = True, -1, 1
                    self.vel_x = 0
            for wall in all_walls:
                if player_rect.colliderect(wall):
                    if self.vel_x > 0:
                        self.x = wall.left - self.width
                        self.on_wall, self.wall_side, self.jumps_left = True, 1, 1
                    elif self.vel_x < 0:
                        self.x = wall.right
                        self.on_wall, self.wall_side, self.jumps_left = True, -1, 1
                    self.vel_x = 0
    
    def take_damage(self, amount, damage_type="normal", source=None):
        if self.invulnerable or self.buffs["evasive_roll"] > 0:
            return 0

        final_damage = amount

        # Shield Stance (Warrior)
        if self.buffs["shield_stance"] > 0:
            final_damage *= 0.85

        # Elemental Shield (Mage)
        if self.buffs["elemental_shield"] > 0 and damage_type == "magic":
            final_damage *= 0.75

        # Parry logic
        if self.parrying:
            final_damage //= 2
            self.quest_progress['warrior_parries'] += 1

            # Warrior Parry effects
            if self.character_class == "Warrior":
                self.buffs["berserk"] = 300 # 5s
                if source and hasattr(source, "take_damage"):
                    source.take_damage(amount * 0.2) # Counter Strike

        self.hp -= final_damage

        # Quest tracking for Rogue: laser damage
        if damage_type == "magic":
            self.laser_damage_taken = True

        return final_damage

    def activate_buff(self, index):
        """index is 1 or 2"""
        buff_key = f"buff{index}"
        if self.buff_cooldowns[buff_key] > 0:
            return False
            
        activated = False
        if self.character_class == "Warrior":
            if index == 1:
                self.buffs["shield_stance"] = 480 # 8s
                activated = True
        elif self.character_class == "Mage":
            mana_cost = 25
            if self.mana >= mana_cost:
                if index == 1:
                    self.buffs["arcane_surge"] = 360 # 6s
                    activated = True
                elif index == 2:
                    self.buffs["elemental_shield"] = 300 # 5s
                    activated = True
                
                if activated:
                    self.mana -= mana_cost
                    self.quest_progress['mage_mana_spent'] += mana_cost
            else:
                return False # Not enough mana
        elif self.character_class == "Archer":
            if index == 1:
                self.buffs["focus_shot"] = True
                activated = True
            elif index == 2:
                self.buffs["evasive_roll"] = 48 # 0.8s
                activated = True
        elif self.character_class == "Rogue":
            if index == 1:
                self.buffs["shadow_dash"] = 60 # 1s
                activated = True
        elif self.character_class == "Reaver":
            if index == 1:
                self.buffs["siphon_strike"] = 300 # 5s
                activated = True
                
        if activated:
            self.buff_cooldowns[buff_key] = self.buff_cooldowns_max[self.character_class][buff_key]
            return True
        return False

    def calculate_damage(self, base_amount, attack_type="melee", target=None):
        final_damage = base_amount

        # Warrior Berserk
        if self.buffs["berserk"] > 0 and attack_type == "melee":
            final_damage *= 1.2

        # Mage Spell Mastery
        if self.character_class == "Mage" and attack_type == "magic":
            final_damage *= 1.15

        # Archer Critical Eye and Focus Shot
        crit_chance = self.crit_chance
        if self.character_class == "Archer":
            crit_chance += 0.1

        if random.random() < crit_chance:
            final_damage *= 1.5
            self.quest_progress['archer_crit_hits'] += 1

        if self.buffs["focus_shot"]:
            final_damage *= 1.4
            self.buffs["focus_shot"] = False # Consumed

        # Rogue Backstab and Critical Timing
        if self.character_class == "Rogue":
            if target and hasattr(target, "facing_right"):
                # If player and target facing same way, it's from behind
                if self.facing_right == target.facing_right:
                    final_damage *= 1.25
                    self.quest_progress['rogue_backstabs'] += 1

            # Critical Timing: +15% damage on consecutive attacks (2s)
            if self.consecutive_attacks > 0:
                final_damage *= 1.15

            self.consecutive_attacks += 1
            self.consecutive_attack_timer = 120 # 2s

        return final_damage

    def on_deal_damage(self, amount):
        heal_amount = 0
        if self.character_class == "Reaver":
            # Life Stealer: +5% HP recovered per attack
            heal_amount += amount * 0.05
            # Siphon Strike: Heal 25% damage dealt for 5s
            if self.buffs["siphon_strike"] > 0:
                heal_amount += amount * 0.25

        if heal_amount > 0:
            self.hp = min(self.max_hp, self.hp + heal_amount)
            self.quest_progress['reaver_hp_siphoned'] += int(heal_amount)

        # Quest progress tracking
        if self.game:
            # Warrior: cumulative damage to boss
            self.quest_progress['warrior_damage'] += amount

            # Archer: range damage to boss/enemies
            if self.weapon_type in ["crossbow", "sniper"]:
                self.quest_progress['archer_range_damage'] += amount

            # Reaver: damage dealt while under 50% HP
            if self.hp < self.max_hp * 0.5:
                self.quest_progress['reaver_low_hp_damage'] += amount

    def jump(self):
        if self.on_ground or self.jumps_left > 0:
            if self.on_wall:
                self.vel_y = -self.jump_power
                self.vel_x = -self.wall_side * self.speed * 2
                self.on_wall = False
                self.jumps_left = 1
            else:
                self.vel_y = -self.jump_power
                self.jumps_left -= 1
    
    def dash(self):
        if self.dash_cooldown == 0:
            self.dashing = True
            self.dash_timer = self.dash_duration
            self.dash_cooldown = self.dash_cooldown_max
            keys = pygame.key.get_pressed()
            if keys[pygame.K_q]:
                self.dash_direction = -1
            elif keys[pygame.K_d]:
                self.dash_direction = 1
            else:
                # Default to facing direction
                self.dash_direction = 1 if self.facing_right else -1
    
    def basic_attack(self):
        if self.attack_cooldown == 0:
            self.attack_cooldown = self.attack_cooldown_max
            return True
        return False
    
    def start_charging(self):
        self.charging = True
        self.charge_percent = 0
    
    def release_charged_attack(self):
        if not self.charging:
            return None
        self.charging = False
        charge = self.charge_percent
        self.charge_percent = 0
        
        # Calculate damage based on weapon
        if self.weapon_type == "crossbow":
            min_dmg, max_dmg = 5, 25
        elif self.weapon_type == "sniper":
            min_dmg, max_dmg = 20, 70
        else:
            min_dmg, max_dmg = 2, 16
        
        damage = min_dmg + (charge - 25) * (max_dmg - min_dmg) / 175
        damage = max(min_dmg, min(max_dmg, damage))
        
        # Apply class multipliers
        attack_type = "magic" if self.character_class == "Mage" else "ranged"
        damage = self.calculate_damage(damage, attack_type)
        
        return {'damage': damage, 'angle': self.aim_angle, 'charge': charge}
    
    def get_charge_color(self):
        if self.charge_percent < 25:
            return BLUE
        elif self.charge_percent < 75:
            return GREEN
        elif self.charge_percent < 150:
            return YELLOW
        else:
            return RED
    
    def draw(self, screen, camera_x, camera_y):
        x, y = self.visual_x - camera_x, self.visual_y - camera_y
        
        # Draw dash trail
        for i, trail in enumerate(self.dash_trail):
            alpha = trail['alpha']
            trail_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            trail_surf.fill((*YELLOW, alpha))
            screen.blit(trail_surf, (trail['x'] - camera_x, trail['y'] - camera_y))
        
        # Apply squash and stretch
        draw_width = self.width
        draw_height = int(self.height * self.squash_stretch)
        height_diff = self.height - draw_height
        
        # Player color with effects
        if self.dashing:
            color = YELLOW
            # Add glow effect
            glow_surf = pygame.Surface((draw_width + 20, draw_height + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*YELLOW, 100), (0, 0, draw_width + 20, draw_height + 20))
            screen.blit(glow_surf, (x - 10, y + height_diff - 10))
        elif self.parrying:
            color = (100, 200, 255)  # Cyan for parry
            # Parry shield effect
            shield_radius = 35 + int(abs(math.sin(self.animation_timer * 0.2)) * 5)
            pygame.draw.circle(screen, (*color, 80), (int(x + draw_width // 2), int(y + draw_height // 2)), shield_radius, 3)
        else:
            color = BLUE
        
        # Draw player with squash/stretch
        pygame.draw.rect(screen, color, (x, y + height_diff, draw_width, draw_height))
        
        # Directional indicator (simple triangle)
        if self.facing_right:
            points = [(x + draw_width, y + height_diff + draw_height // 2),
                     (x + draw_width - 10, y + height_diff + draw_height // 2 - 5),
                     (x + draw_width - 10, y + height_diff + draw_height // 2 + 5)]
        else:
            points = [(x, y + height_diff + draw_height // 2),
                     (x + 10, y + height_diff + draw_height // 2 - 5),
                     (x + 10, y + height_diff + draw_height // 2 + 5)]
        pygame.draw.polygon(screen, WHITE, points)
        
        if self.charging:
            center_x, center_y = x + draw_width // 2, y + height_diff + draw_height // 2
            
            if self.weapon_type == "sniper":
                # Draw circular POV cursor at mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                # Animated crosshair
                crosshair_size = 30 + int(abs(math.sin(self.animation_timer * 0.1)) * 5)
                pygame.draw.circle(screen, RED, (mouse_x, mouse_y), crosshair_size, 2)
                pygame.draw.circle(screen, RED, (mouse_x, mouse_y), 5)
                
                # Crosshair lines with animation
                line_offset = 25 + int(abs(math.sin(self.animation_timer * 0.1)) * 5)
                pygame.draw.line(screen, RED, (mouse_x - crosshair_size - 10, mouse_y), (mouse_x - line_offset, mouse_y), 2)
                pygame.draw.line(screen, RED, (mouse_x + crosshair_size + 10, mouse_y), (mouse_x + line_offset, mouse_y), 2)
                pygame.draw.line(screen, RED, (mouse_x, mouse_y - crosshair_size - 10), (mouse_x, mouse_y - line_offset), 2)
                pygame.draw.line(screen, RED, (mouse_x, mouse_y + crosshair_size + 10), (mouse_x, mouse_y + line_offset), 2)
                
                # Charge indicator around cursor
                charge_arc = (self.charge_percent / self.max_charge) * 360
                if charge_arc > 0:
                    rect = pygame.Rect(mouse_x - 40, mouse_y - 40, 80, 80)
                    pygame.draw.arc(screen, self.get_charge_color(), rect, 0, math.radians(charge_arc), 5)
            else:
                # Regular beam with animated thickness
                beam_length = 600 if self.weapon_type == "crossbow" else 300
                end_x = center_x + math.cos(self.aim_angle) * beam_length
                end_y = center_y + math.sin(self.aim_angle) * beam_length
                beam_color = self.get_charge_color()
                thickness = 3 + int(self.charge_percent / 50) + int(abs(math.sin(self.animation_timer * 0.2)) * 2)
                
                # Draw beam with glow
                pygame.draw.line(screen, (*beam_color, 100), (center_x, center_y), (end_x, end_y), thickness + 4)
                pygame.draw.line(screen, beam_color, (center_x, center_y), (end_x, end_y), thickness)
                
                # Animated charge indicator
                charge_radius = 10 + int(self.charge_percent / 20) + int(abs(math.sin(self.animation_timer * 0.15)) * 3)
                pygame.draw.circle(screen, beam_color, (int(end_x), int(end_y)), charge_radius, 2)
                pygame.draw.circle(screen, (*beam_color, 50), (int(end_x), int(end_y)), charge_radius + 5, 2)
        
        # Health bar with smooth transitions
        bar_width, bar_height = 60, 8
        pygame.draw.rect(screen, RED, (x - 10, y - 20, bar_width, bar_height))
        health_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (x - 10, y - 20, health_width, bar_height))
        
        # Dash cooldown with color gradient
        if self.dash_cooldown > 0:
            cooldown_width = int((self.dash_cooldown / self.dash_cooldown_max) * bar_width)
            cooldown_color = ORANGE if self.dash_cooldown < 10 else (200, 100, 0)
            pygame.draw.rect(screen, cooldown_color, (x - 10, y - 30, cooldown_width, 4))
            
        # Mana bar for Mage
        if self.character_class == "Mage":
            mana_width = int((self.mana / self.max_mana) * bar_width)
            pygame.draw.rect(screen, BLUE, (x - 10, y - 35, mana_width, 4))

        # Buff cooldowns
        curr_y = y - 45
        for i in [1, 2]:
            buff_key = f"buff{i}"
            if self.character_class in self.buff_cooldowns_max:
                cooldown = self.buff_cooldowns[buff_key]
                max_cooldown = self.buff_cooldowns_max[self.character_class][buff_key]
                if max_cooldown > 0:
                    pygame.draw.rect(screen, DARK_GRAY, (x - 10, curr_y, bar_width, 3))
                    if cooldown > 0:
                        cd_width = int((cooldown / max_cooldown) * bar_width)
                        pygame.draw.rect(screen, YELLOW, (x - 10, curr_y, cd_width, 3))
                    else:
                        pygame.draw.rect(screen, WHITE, (x - 10, curr_y, bar_width, 3))
                    curr_y -= 5

class Boss:
    def __init__(self):
        self.width, self.height = 120, 140
        self.x, self.y = MAP_WIDTH // 2, 100
        self.max_hp, self.hp = 500, 500
        self.speed = 4
        self.hits_taken = 0
        self.move_timer = 0
        self.target_x = self.x
        self.phase = 1
        
        self.fireball_cooldown_max_base = 120
        self.laser_cooldown_max_base = 240
        self.shockwave_cooldown_max_base = 480
        self.minion_cooldown_max_base = 720
        
        self.fireball_cooldown_max = 120
        self.laser_cooldown_max = 240
        self.shockwave_cooldown_max = 480
        self.minion_cooldown_max = 720
        
        self.fireball_cooldown = 0
        self.laser_cooldown = 0
        self.shockwave_cooldown = 240
        self.minion_cooldown = 360
        self.flash_timer = 0
        
        # Phase 2 transition animation
        self.phase2_transition_active = False
        self.phase2_transition_timer = 0
        self.phase2_transition_duration = 180  # 3 seconds at 60 FPS
        self.phase2_glow_pulse = 0
        
        # Smooth movement
        self.visual_x = self.x
        self.visual_y = self.y
    
    def update(self, game=None):
        if self.fireball_cooldown > 0:
            self.fireball_cooldown -= 1
        if self.laser_cooldown > 0:
            self.laser_cooldown -= 1
        if self.shockwave_cooldown > 0:
            self.shockwave_cooldown -= 1
        if self.minion_cooldown > 0:
            self.minion_cooldown -= 1
        if self.flash_timer > 0:
            self.flash_timer -= 1
        
        # Phase 2 transition
        if self.phase2_transition_active:
            self.phase2_transition_timer += 1
            self.phase2_glow_pulse = abs(math.sin(self.phase2_transition_timer * 0.1)) * 50
            
            if self.phase2_transition_timer >= self.phase2_transition_duration:
                self.phase2_transition_active = False
                self.phase2_transition_timer = 0
            return  # Don't move during transition
        
        # Check for Phase 2 entry - Blocked by minibosses
        can_enter_phase2 = True
        if game and hasattr(game, 'miniboss_phase_completed'):
            can_enter_phase2 = game.miniboss_phase_completed
            
        if self.hp <= self.max_hp // 2 and self.phase == 1 and can_enter_phase2:
            self.phase = 2
            self.phase2_transition_active = True
            self.phase2_transition_timer = 0
            self.fireball_cooldown_max = self.fireball_cooldown_max_base // 3
            self.laser_cooldown_max = self.laser_cooldown_max_base // 3
            self.shockwave_cooldown_max = self.shockwave_cooldown_max_base // 3
            self.minion_cooldown_max = self.minion_cooldown_max_base // 3
        
        if self.move_timer <= 0:
            self.target_x = random.randint(200, MAP_WIDTH - 200)
            self.move_timer = random.randint(60, 180)
        
        if abs(self.x - self.target_x) > 5:
            self.x += self.speed if self.x < self.target_x else -self.speed
        
        self.move_timer -= 1
        self.x = max(100, min(self.x, MAP_WIDTH - 100))
        
        # Smooth visual position
        self.visual_x += (self.x - self.visual_x) * 0.3
        self.visual_y += (self.y - self.visual_y) * 0.3
    
    def take_damage(self, damage):
        self.hp -= damage
        self.hits_taken += 1
        self.flash_timer = 5
    
    def draw(self, screen, camera_x, camera_y):
        x, y = self.visual_x - camera_x, self.visual_y - camera_y
        
        # Phase 2 transition effect
        if self.phase2_transition_active:
            # Pulsing glow effect
            glow_radius = int(120 + self.phase2_glow_pulse)
            for i in range(3):
                alpha_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                alpha = int(100 - i * 30)
                pygame.draw.circle(alpha_surf, (*RED, alpha), (glow_radius, glow_radius), glow_radius - i * 20)
                screen.blit(alpha_surf, (x + self.width // 2 - glow_radius, y + self.height // 2 - glow_radius))
            
            # Oscillating color
            progress = self.phase2_transition_timer / self.phase2_transition_duration
            color_intensity = int(abs(math.sin(progress * math.pi * 4)) * 255)
            transition_color = (color_intensity, 0, 255 - color_intensity)
            pygame.draw.rect(screen, transition_color, (x, y, self.width, self.height))
            
            # Energy particles
            for i in range(8):
                angle = (self.phase2_transition_timer + i * 45) * 0.1
                particle_x = x + self.width // 2 + math.cos(angle) * 80
                particle_y = y + self.height // 2 + math.sin(angle) * 80
                particle_size = 5 + int(abs(math.sin(angle * 2)) * 5)
                pygame.draw.circle(screen, ORANGE, (int(particle_x), int(particle_y)), particle_size)
        else:
            # Normal boss rendering
            color = WHITE if self.flash_timer > 0 else (RED if self.phase == 2 else PURPLE)
            
            # Phase 2 subtle glow
            if self.phase == 2:
                glow_pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 20
                for i in range(2):
                    alpha_surf = pygame.Surface((self.width + 20, self.height + 20), pygame.SRCALPHA)
                    alpha = int(50 - i * 20)
                    pygame.draw.rect(alpha_surf, (*RED, alpha), (0, 0, self.width + 20, self.height + 20))
                    screen.blit(alpha_surf, (x - 10, y - 10))
            
            pygame.draw.rect(screen, color, (x, y, self.width, self.height))
        
        # Health bar
        bar_width, bar_height = 400, 20
        bar_x = SCREEN_WIDTH // 2 - bar_width // 2
        pygame.draw.rect(screen, RED, (bar_x, 20, bar_width, bar_height))
        health_width = int((self.hp / self.max_hp) * bar_width)
        bar_color = ORANGE if self.phase == 2 else GREEN
        pygame.draw.rect(screen, bar_color, (bar_x, 20, health_width, bar_height))
        
        if self.phase == 2:
            phase_font = pygame.font.Font(None, 36)
            phase_text = phase_font.render("PHASE 2", True, RED)
            screen.blit(phase_text, (bar_x + bar_width + 20, 15))

class Projectile:
    def __init__(self, x, y, vel_x, vel_y, damage, proj_type):
        self.x, self.y = x, y
        self.vel_x, self.vel_y = vel_x, vel_y
        self.damage = damage
        self.type = proj_type
        self.radius = 15 if proj_type == 'fireball' else 10
    
    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        if self.type == 'fireball':
            self.vel_y += 0.4
    
    def draw(self, screen, camera_x, camera_y):
        x, y = int(self.x - camera_x), int(self.y - camera_y)
        if self.type == 'charged_attack':
            pygame.draw.circle(screen, WHITE, (x, y), self.radius)
            pygame.draw.circle(screen, BLUE, (x, y), self.radius - 3)
        else:
            color = ORANGE if self.type == 'fireball' else RED
            pygame.draw.circle(screen, color, (x, y), self.radius)

class Minion:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.width, self.height = 30, 30
        self.speed = 4
        self.vel_y = 0
        self.gravity = 0.6
    
    def update(self, player, platforms):
        self.x += -self.speed if player.x < self.x else self.speed
        self.vel_y += self.gravity
        self.y += self.vel_y
        
        minion_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for platform in platforms:
            if minion_rect.colliderect(platform) and self.vel_y > 0:
                self.y = platform.top - self.height
                self.vel_y = 0
    
    def draw(self, screen, camera_x, camera_y):
        pygame.draw.rect(screen, DARK_PURPLE, (self.x - camera_x, self.y - camera_y, self.width, self.height))

class HealingOrb:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 15
        self.heal_amount = 30
        self.pulse_timer = 0
    
    def update(self):
        self.pulse_timer += 1
    
    def draw(self, screen, camera_x, camera_y):
        x, y = int(self.x - camera_x), int(self.y - camera_y)
        pulse = abs(math.sin(self.pulse_timer * 0.1)) * 3
        current_radius = self.radius + int(pulse)
        pygame.draw.circle(screen, (0, 255, 100), (x, y), current_radius + 3)
        pygame.draw.circle(screen, GREEN, (x, y), current_radius)

# MiniBoss class
class MiniBoss:
    def __init__(self, side):
        self.side = side
        self.width, self.height = 80, 100
        # Positioned on the left/right pylons (platforms at 300 and 1800)
        self.x = 410 if side == "left" else 1910
        self.y = MAP_HEIGHT - 300
        self.max_hp, self.hp = 100, 100
        self.flash_timer = 0
        
        self.energy_link_cooldown = 0
        self.energy_link_cooldown_max = 240
        self.overload_cooldown = 0
        self.overload_cooldown_max = 300
        self.summon_cooldown = 0
        self.summon_cooldown_max = 360
        
        # Initialize all cooldowns for both sides (they may be swapped during gameplay)
        self.orb_rain_cooldown = 0
        self.orb_rain_cooldown_max = 180
        self.confinement_cooldown = 0
        self.confinement_cooldown_max = 420
        self.gravity_mark_cooldown = 0
        self.gravity_mark_cooldown_max = 480
        self.pierce_shot_cooldown = 0
        self.pierce_shot_cooldown_max = 150
        self.laser_lock_cooldown = 0
        self.laser_lock_cooldown_max = 360
        self.lightning_cooldown = 0
        self.lightning_cooldown_max = 300
        
        self.overload_charge = 0
        self.overload_active = False
        
        if side == "left":
            self.laser_locking = False
            self.laser_lock_timer = 0
        else:
            self.laser_locking = False
            self.laser_lock_timer = 0
        
        self.enrage_level = 0
        self.attack_speed_multiplier = 1.0
        self.post_switch_boost = False
        self.post_switch_boost_timer = 0
        
    def update(self, other_miniboss):
        if self.flash_timer > 0:
            self.flash_timer -= 1
        
        if self.post_switch_boost:
            self.post_switch_boost_timer -= 1
            if self.post_switch_boost_timer <= 0:
                self.post_switch_boost = False
                self.attack_speed_multiplier = 1.0
        
        cooldown_mult = self.attack_speed_multiplier * (1.0 - self.enrage_level * 0.15)
        
        if self.energy_link_cooldown > 0:
            self.energy_link_cooldown -= cooldown_mult
        if self.overload_cooldown > 0:
            self.overload_cooldown -= cooldown_mult
        if self.summon_cooldown > 0:
            self.summon_cooldown -= cooldown_mult
        
        if self.side == "left":
            if self.orb_rain_cooldown > 0:
                self.orb_rain_cooldown -= cooldown_mult
            if self.confinement_cooldown > 0:
                self.confinement_cooldown -= cooldown_mult
            if self.gravity_mark_cooldown > 0:
                self.gravity_mark_cooldown -= cooldown_mult
        else:
            if self.pierce_shot_cooldown > 0:
                self.pierce_shot_cooldown -= cooldown_mult
            if self.laser_lock_cooldown > 0:
                self.laser_lock_cooldown -= cooldown_mult
            if self.lightning_cooldown > 0:
                self.lightning_cooldown -= cooldown_mult
            if self.laser_locking:
                self.laser_lock_timer -= 1
        
        if self.overload_active:
            self.overload_charge += 1
    
    def take_damage(self, damage):
        self.hp -= damage
        self.flash_timer = 5
        
        hp_ratio = self.hp / self.max_hp
        if hp_ratio < 0.7 and self.enrage_level < 1:
            self.enrage_level = 1
        elif hp_ratio < 0.4 and self.enrage_level < 2:
            self.enrage_level = 2
    
    def switch_position(self, other_x):
        self.x = other_x
        self.side = "left" if self.side == "right" else "right"
        self.post_switch_boost = True
        self.post_switch_boost_timer = 180
        self.attack_speed_multiplier = 1.5
    
    def draw(self, screen, camera_x, camera_y):
        x, y = self.x - camera_x, self.y - camera_y
        
        color = WHITE if self.flash_timer > 0 else (BLUE if self.side == "left" else ORANGE)
        
        if self.overload_active:
            glow_radius = int(60 + self.overload_charge * 0.3)
            for i in range(3):
                alpha_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                alpha = int(80 - i * 25)
                pygame.draw.circle(alpha_surf, (*YELLOW, alpha), (glow_radius, glow_radius), glow_radius - i * 10)
                screen.blit(alpha_surf, (x + self.width // 2 - glow_radius, y + self.height // 2 - glow_radius))
        
        pygame.draw.rect(screen, color, (x, y, self.width, self.height))
        
        bar_width = 100
        pygame.draw.rect(screen, RED, (x - 10, y - 20, bar_width, 8))
        health_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (x - 10, y - 20, health_width, 8))
        
        if self.enrage_level > 0:
            enrage_color = ORANGE if self.enrage_level == 1 else RED
            pygame.draw.rect(screen, enrage_color, (x, y, self.width, self.height), 3)

# MiniBossManager class
class MiniBossManager:
    def __init__(self):
        self.left_boss = MiniBoss("left")
        self.right_boss = MiniBoss("right")
        self.switch_timer = 1800
        self.switch_cooldown = 1800
        self.active = False
        self.energy_link_active = False
        self.energy_link_damage_timer = 0
        self.persistent_orbs = []
        self.confinement_zones = []
        self.gravity_marks = []
        self.lightning_zones = []
        self.pierce_shots = []
        self.switch_explosions = []
        
    def update(self, player, projectiles, minions):
        if not self.active or not self.left_boss or not self.right_boss:
            return
        
        if self.left_boss.hp <= 0:
            self.left_boss = None
        if self.right_boss.hp <= 0:
            self.right_boss = None
        
        if not self.left_boss or not self.right_boss:
            self.active = False
            return
        
        self.left_boss.update(self.right_boss)
        self.right_boss.update(self.left_boss)
        
        self.switch_timer -= 1
        if self.switch_timer <= 0:
            self.execute_switch(projectiles)
            base_cooldown = 1800 - self.left_boss.enrage_level * 600
            self.switch_cooldown = max(1200, base_cooldown)
            self.switch_timer = self.switch_cooldown
        
        self.update_attacks(player, projectiles, minions)
        self.update_persistent_effects(player)
    
    def execute_switch(self, projectiles):
        old_left_x = self.left_boss.x
        old_right_x = self.right_boss.x
        
        self.left_boss.switch_position(old_right_x)
        self.right_boss.switch_position(old_left_x)
        
        # Reset pylon overload after swap
        self.left_boss.overload_active = False
        self.left_boss.overload_charge = 0
        self.right_boss.overload_active = False
        self.right_boss.overload_charge = 0
        
        for x_pos in [old_left_x, old_right_x]:
            self.switch_explosions.append({
                'x': x_pos,
                'y': self.left_boss.y,
                'radius': 0,
                'max_radius': 150,
                'timer': 30,
                'damage_dealt': False
            })
        
        # Exchange one signature attack between the two mini-bosses
        # Signature 1: Orb Rain vs Pierce Shot
        temp_rain = self.left_boss.orb_rain_cooldown
        self.left_boss.orb_rain_cooldown = self.right_boss.pierce_shot_cooldown
        self.right_boss.pierce_shot_cooldown = temp_rain
        
        # We also need to swap the logic assignment flag if we use one
        # For now, we'll swap who is responsible for which attack in update_attacks
        self.swapped_signature = not getattr(self, 'swapped_signature', False)
    
    def update_attacks(self, player, projectiles, minions):
        # Persistent energy link dealing continuous damage
        if self.left_boss and self.right_boss:
            self.energy_link_active = True
            self.energy_link_damage_timer += 1
            if self.energy_link_damage_timer >= 60:
                self.energy_link_damage_timer = 0
        else:
            self.energy_link_active = False
        
        if self.left_boss.overload_cooldown <= 0:
            self.left_boss.overload_active = True
            self.left_boss.overload_charge = 0
            self.left_boss.overload_cooldown = self.left_boss.overload_cooldown_max
        
        if self.right_boss.overload_cooldown <= 0:
            self.right_boss.overload_active = True
            self.right_boss.overload_charge = 0
            self.right_boss.overload_cooldown = self.right_boss.overload_cooldown_max
        
        if self.left_boss.summon_cooldown <= 0 and self.right_boss.summon_cooldown <= 0:
            count = 2 + self.left_boss.enrage_level
            for _ in range(count):
                spawn_x = random.choice([self.left_boss.x, self.right_boss.x]) + random.randint(-50, 50)
                minions.append(Minion(spawn_x, self.left_boss.y + 100))
            self.left_boss.summon_cooldown = self.left_boss.summon_cooldown_max
            self.right_boss.summon_cooldown = self.right_boss.summon_cooldown_max
        
        # Determine who handles which signature attack
        boss_a = self.right_boss if getattr(self, 'swapped_signature', False) else self.left_boss
        boss_b = self.left_boss if getattr(self, 'swapped_signature', False) else self.right_boss
        
        if boss_a.orb_rain_cooldown <= 0:
            count = 5 + boss_a.enrage_level * 3
            for _ in range(count):
                orb_x = random.randint(200, MAP_WIDTH - 200)
                self.persistent_orbs.append({
                    'x': orb_x,
                    'y': 0,
                    'vel_y': random.uniform(3, 6),
                    'radius': 12,
                    'lifetime': 600
                })
            boss_a.orb_rain_cooldown = boss_a.orb_rain_cooldown_max
        
        if self.left_boss.confinement_cooldown <= 0:
            self.confinement_zones.append({
                'x': player.x,
                'y': player.y,
                'radius': 200,
                'timer': 180,
                'strength': 0.7
            })
            self.left_boss.confinement_cooldown = self.left_boss.confinement_cooldown_max
        
        if self.left_boss.gravity_mark_cooldown <= 0:
            self.gravity_marks.append({
                'x': player.x,
                'y': player.y,
                'delay': 120,
                'active': False,
                'pull_strength': 8
            })
            self.left_boss.gravity_mark_cooldown = self.left_boss.gravity_mark_cooldown_max
        
        if boss_b.pierce_shot_cooldown <= 0:
            count = 3 + boss_b.enrage_level
            for _ in range(count):
                dx = player.x - boss_b.x
                dy = player.y - boss_b.y
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0:
                    vel_x = (dx / dist) * 12
                    vel_y = (dy / dist) * 12
                    self.pierce_shots.append({
                        'x': boss_b.x + boss_b.width // 2,
                        'y': boss_b.y + boss_b.height // 2,
                        'vel_x': vel_x,
                        'vel_y': vel_y,
                        'damage': 15,
                        'pierced': 0
                    })
            boss_b.pierce_shot_cooldown = boss_b.pierce_shot_cooldown_max
        
        if self.right_boss.laser_lock_cooldown <= 0 and not self.right_boss.laser_locking:
            self.right_boss.laser_locking = True
            self.right_boss.laser_lock_timer = 120
            self.right_boss.laser_lock_cooldown = self.right_boss.laser_lock_cooldown_max
        
        if self.right_boss.laser_locking and self.right_boss.laser_lock_timer <= 0:
            dx = player.x - self.right_boss.x
            dy = player.y - self.right_boss.y
            angle = math.atan2(dy, dx)
            speed = 20
            projectiles.append(Projectile(
                self.right_boss.x + self.right_boss.width // 2,
                self.right_boss.y + self.right_boss.height // 2,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                40,
                'laser_blast'
            ))
            self.right_boss.laser_locking = False
        
        if self.right_boss.lightning_cooldown <= 0:
            self.lightning_zones.append({
                'x': player.x,
                'y': player.y,
                'radius': 80,
                'timer': 300,
                'damage_interval': 30,
                'damage_timer': 0
            })
            self.right_boss.lightning_cooldown = self.right_boss.lightning_cooldown_max
    
    def update_persistent_effects(self, player):
        for orb in self.persistent_orbs[:]:
            orb['y'] += orb['vel_y']
            orb['lifetime'] -= 1
            if orb['lifetime'] <= 0 or orb['y'] > MAP_HEIGHT:
                self.persistent_orbs.remove(orb)
        
        for zone in self.confinement_zones[:]:
            zone['timer'] -= 1
            if zone['timer'] <= 0:
                self.confinement_zones.remove(zone)
            else:
                dx = player.x - zone['x']
                dy = player.y - zone['y']
                dist = math.sqrt(dx**2 + dy**2)
                if dist < zone['radius']:
                    player.external_slow = min(getattr(player, 'external_slow', 1.0), zone['strength'])
        
        for mark in self.gravity_marks[:]:
            if not mark['active']:
                mark['delay'] -= 1
                if mark['delay'] <= 0:
                    mark['active'] = True
            else:
                dx = mark['x'] - player.x
                dy = mark['y'] - player.y
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0 and dist < 400:
                    player.vel_x += (dx / dist) * mark['pull_strength'] * 0.1
                    player.vel_y += (dy / dist) * mark['pull_strength'] * 0.1
                mark['pull_strength'] *= 0.98
                if mark['pull_strength'] < 1:
                    self.gravity_marks.remove(mark)
        
        for zone in self.lightning_zones[:]:
            zone['timer'] -= 1
            zone['damage_timer'] += 1
            if zone['timer'] <= 0:
                self.lightning_zones.remove(zone)
        
        for shot in self.pierce_shots[:]:
            shot['x'] += shot['vel_x']
            shot['y'] += shot['vel_y']
            if shot['x'] < 0 or shot['x'] > MAP_WIDTH or shot['y'] < 0 or shot['y'] > MAP_HEIGHT:
                self.pierce_shots.remove(shot)
            elif shot['pierced'] >= 3:
                self.pierce_shots.remove(shot)
        
        for explosion in self.switch_explosions[:]:
            explosion['timer'] -= 1
            explosion['radius'] = (1 - explosion['timer'] / 30) * explosion['max_radius']
            if explosion['timer'] <= 0:
                self.switch_explosions.remove(explosion)
    
    def check_damage_to_player(self, player):
        if player.invulnerable or player.dashing:
            return
        
        player_rect = pygame.Rect(player.x, player.y, player.width, player.height)
        
        if self.energy_link_active and self.energy_link_damage_timer == 0:
            # Check if player intersects the line between bosses
            x1, y1 = self.left_boss.x + self.left_boss.width // 2, self.left_boss.y + self.left_boss.height // 2
            x2, y2 = self.right_boss.x + self.right_boss.width // 2, self.right_boss.y + self.right_boss.height // 2
            px, py = player.x + player.width // 2, player.y + player.height // 2
            
            # Distance from point to line segment
            line_len = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            if line_len > 0:
                t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_len**2)))
                proj_x = x1 + t * (x2 - x1)
                proj_y = y1 + t * (y2 - y1)
                dist = math.sqrt((px - proj_x)**2 + (py - proj_y)**2)
                
                if dist < 40:  # Within link thickness
                    player.take_damage(6, "magic", self)
        
        for boss in [self.left_boss, self.right_boss]:
            if boss and boss.overload_active:
                dx = player.x - boss.x
                dy = player.y - boss.y
                dist = math.sqrt(dx**2 + dy**2)
                damage_radius = 60 + boss.overload_charge * 0.3
                if dist < damage_radius:
                    damage = int((boss.overload_charge / 100) * 15)
                    if damage > 0:
                        player.take_damage(damage, "magic", boss)
                        boss.overload_active = False
                        boss.overload_charge = 0
        
        for orb in self.persistent_orbs[:]:
            orb_rect = pygame.Rect(orb['x'] - orb['radius'], orb['y'] - orb['radius'], orb['radius'] * 2, orb['radius'] * 2)
            if player_rect.colliderect(orb_rect):
                player.take_damage(8, "magic", self)
                self.persistent_orbs.remove(orb)
        
        for zone in self.lightning_zones:
            dx = player.x - zone['x']
            dy = player.y - zone['y']
            dist = math.sqrt(dx**2 + dy**2)
            if dist < zone['radius'] and zone['damage_timer'] >= zone['damage_interval']:
                player.take_damage(10, "magic", self)
                zone['damage_timer'] = 0
        
        for shot in self.pierce_shots[:]:
            shot_rect = pygame.Rect(shot['x'] - 8, shot['y'] - 8, 16, 16)
            if player_rect.colliderect(shot_rect):
                player.take_damage(shot['damage'], "normal", self)
                shot['pierced'] += 1
        
        for explosion in self.switch_explosions:
            if not explosion['damage_dealt'] and explosion['timer'] <= 20:
                dx = player.x - explosion['x']
                dy = player.y - explosion['y']
                dist = math.sqrt(dx**2 + dy**2)
                if dist < explosion['radius']:
                    player.take_damage(30, "normal", self)
                    explosion['damage_dealt'] = True
    
    def draw(self, screen, camera_x, camera_y):
        if not self.active:
            return
        
        if self.left_boss:
            self.left_boss.draw(screen, camera_x, camera_y)
        if self.right_boss:
            self.right_boss.draw(screen, camera_x, camera_y)
        
        if self.energy_link_active and self.left_boss and self.right_boss:
            lx = self.left_boss.x + self.left_boss.width // 2 - camera_x
            ly = self.left_boss.y + self.left_boss.height // 2 - camera_y
            rx = self.right_boss.x + self.right_boss.width // 2 - camera_x
            ry = self.right_boss.y + self.right_boss.height // 2 - camera_y
            
            for i in range(5):
                alpha = 50 + i * 30
                color = (*PURPLE, alpha)
                thickness = 8 - i
                link_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(link_surf, color, (lx, ly), (rx, ry), thickness)
                screen.blit(link_surf, (0, 0))
        
        for orb in self.persistent_orbs:
            orb_x = orb['x'] - camera_x
            orb_y = orb['y'] - camera_y
            pygame.draw.circle(screen, BLUE, (int(orb_x), int(orb_y)), orb['radius'])
            pygame.draw.circle(screen, WHITE, (int(orb_x), int(orb_y)), orb['radius'] - 3)
        
        for zone in self.confinement_zones:
            zone_x = zone['x'] - camera_x
            zone_y = zone['y'] - camera_y
            surf = pygame.Surface((zone['radius'] * 2, zone['radius'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*BLUE, 80), (zone['radius'], zone['radius']), zone['radius'])
            screen.blit(surf, (zone_x - zone['radius'], zone_y - zone['radius']))
            pygame.draw.circle(screen, BLUE, (int(zone_x), int(zone_y)), zone['radius'], 2)
        
        for mark in self.gravity_marks:
            mark_x = mark['x'] - camera_x
            mark_y = mark['y'] - camera_y
            if mark['active']:
                pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.01)) * 20)
                radius = 30 + pulse
                pygame.draw.circle(screen, PURPLE, (int(mark_x), int(mark_y)), radius, 3)
                pygame.draw.circle(screen, (*PURPLE, 50), (int(mark_x), int(mark_y)), radius - 5, 2)
            else:
                pygame.draw.circle(screen, (*PURPLE, 100), (int(mark_x), int(mark_y)), 20, 2)
        
        for zone in self.lightning_zones:
            zone_x = zone['x'] - camera_x
            zone_y = zone['y'] - camera_y
            surf = pygame.Surface((zone['radius'] * 2, zone['radius'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*YELLOW, 60), (zone['radius'], zone['radius']), zone['radius'])
            screen.blit(surf, (zone_x - zone['radius'], zone_y - zone['radius']))
            
            for _ in range(3):
                offset_x = random.randint(-zone['radius'], zone['radius'])
                offset_y = random.randint(-zone['radius'], zone['radius'])
                pygame.draw.line(screen, YELLOW, (int(zone_x), int(zone_y)), (int(zone_x + offset_x), int(zone_y + offset_y)), 2)
        
        for shot in self.pierce_shots:
            shot_x = shot['x'] - camera_x
            shot_y = shot['y'] - camera_y
            pygame.draw.circle(screen, ORANGE, (int(shot_x), int(shot_y)), 8)
            
            angle = math.atan2(shot['vel_y'], shot['vel_x'])
            tail_x = shot_x - math.cos(angle) * 20
            tail_y = shot_y - math.sin(angle) * 20
            pygame.draw.line(screen, ORANGE, (int(shot_x), int(shot_y)), (int(tail_x), int(tail_y)), 3)
        
        for explosion in self.switch_explosions:
            exp_x = explosion['x'] - camera_x
            exp_y = explosion['y'] - camera_y
            surf = pygame.Surface((explosion['radius'] * 2, explosion['radius'] * 2), pygame.SRCALPHA)
            alpha = int((explosion['timer'] / 30) * 150)
            pygame.draw.circle(surf, (*RED, alpha), (int(explosion['radius']), int(explosion['radius'])), int(explosion['radius']))
            screen.blit(surf, (exp_x - explosion['radius'], exp_y - explosion['radius']))
            pygame.draw.circle(screen, ORANGE, (int(exp_x), int(exp_y)), int(explosion['radius']), 3)
        
        if self.right_boss and self.right_boss.laser_locking:
            lock_x = self.right_boss.x + self.right_boss.width // 2 - camera_x
            lock_y = self.right_boss.y + self.right_boss.height // 2 - camera_y
            
            for i in range(3):
                radius = 40 + i * 15
                alpha = int(150 - i * 40)
                surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*RED, alpha), (radius, radius), radius, 3)
                screen.blit(surf, (lock_x - radius, lock_y - radius))

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("Hollow Knight Boss Fight - Enhanced")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MAIN_MENU
        self.last_state = GameState.MAIN_MENU
        
        self.player = None
        self.boss = None
        self.projectiles = []
        self.minions = []
        self.fire_zones = []
        self.lasers = []
        self.temp_walls = []
        self.healing_orbs = []
        self.orb_spawn_timer = 0
        self.laser_spawn_queue = []
        
        self.platforms = []
        self.walls = []
        self.setup_arena()
        
        self.camera_x, self.camera_y = 0, 0
        
        # Menu system
        self.menu = Menu()
        self.shop = Shop()
        self.save_manager = SaveManager()
        
        self.miniboss_manager = MiniBossManager()
        self.miniboss_phase_completed = False
        self.selected_character = None

        # Meta progression data (persists between runs)
        self.currency = 0  # Loaded from meta save
        self.total_damage_dealt = 0  # Runtime only - NOT saved
        self.unlocked_classes = set()  # Loaded from meta save
        self.mastery_unlocks = set()   # Loaded from meta save
        self.meta_quest_progress = {
            'warrior_damage': 0,
            'mage_crystals': 0,
            'archer_range_damage': 0,
            'rogue_laser_avoids': 0,
            'reaver_low_hp_damage': 0,
            'warrior_parries': 0,
            'mage_mana_spent': 0,
            'archer_crit_hits': 0,
            'rogue_backstabs': 0,
            'reaver_hp_siphoned': 0
        }

        # Quest definitions
        self.quests = {
            'warrior_damage': {
                'name': 'Warrior\'s Fury',
                'class': 'Warrior',
                'description': 'Deal 100 damage to the boss',
                'max_progress': 100,
                'reward': 'Unlock Warrior class'
            },
            'mage_crystals': {
                'name': 'Crystal Collector',
                'class': 'Mage',
                'description': 'Collect 5 crystals',
                'max_progress': 5,
                'reward': 'Unlock Mage class'
            },
            'archer_range_damage': {
                'name': 'Marksman\'s Precision',
                'class': 'Archer',
                'description': 'Deal 100 ranged damage to enemies',
                'max_progress': 100,
                'reward': 'Unlock Archer class'
            },
            'rogue_laser_avoids': {
                'name': 'Shadow Dancer',
                'class': 'Rogue',
                'description': 'Avoid 10 laser attacks',
                'max_progress': 10,
                'reward': 'Unlock Rogue class'
            },
            'reaver_low_hp_damage': {
                'name': 'Survivor\'s Rage',
                'class': 'Reaver',
                'description': 'Deal 100 damage while under 50% HP',
                'max_progress': 100,
                'reward': 'Unlock Reaver class'
            },
            'warrior_parries': {
                'name': 'Shield Master',
                'class': 'Warrior',
                'description': 'Successfully parry 10 attacks',
                'max_progress': 10,
                'reward': 'Warrior Mastery'
            },
            'mage_mana_spent': {
                'name': 'Arcane Scholar',
                'class': 'Mage',
                'description': 'Spend 500 mana on abilities',
                'max_progress': 500,
                'reward': 'Mage Mastery'
            },
            'archer_crit_hits': {
                'name': 'Eagle Eye',
                'class': 'Archer',
                'description': 'Land 20 critical hits',
                'max_progress': 20,
                'reward': 'Archer Mastery'
            },
            'rogue_backstabs': {
                'name': 'Ghost Assassin',
                'class': 'Rogue',
                'description': 'Perform 50 backstab attacks',
                'max_progress': 50,
                'reward': 'Rogue Mastery'
            },
            'reaver_hp_siphoned': {
                'name': 'Blood Drinker',
                'class': 'Reaver',
                'description': 'Siphon 200 total HP from enemies',
                'max_progress': 200,
                'reward': 'Reaver Mastery'
            }
        }

        # Quest elements
        self.crystals = []
        self.laser_attack_timer = 0

        # Load meta progression on startup
        self.load_meta_progression()
        
        # Platform hazard system
        self.platform_disappear_timer = 0
        self.platforms_visible = True
        self.platform_hazard_active = False
        
        # Admin panel (from original)
        self.admin_panel_active = False
        self.admin_input = ""
        self.admin_history = []
        self.godmode = False
        self.boss_invincible = False
        self.paused = False
        self.camera_follow = True
        self.debug_mode = False
        self.admin_authenticated = False
        self.admin_login_mode = False
        self.admin_username = ""
        self.admin_password = ""
        self.admin_input_field = "username"
        self.admin_login_attempts = 0
    
    def setup_arena(self):
        self.platforms.append(pygame.Rect(0, MAP_HEIGHT - 50, MAP_WIDTH, 50))
        for i in range(4):
            self.platforms.append(pygame.Rect(300 + i * 500, MAP_HEIGHT - 200, 300, 20))
        for i in range(5):
            self.platforms.append(pygame.Rect(150 + i * 450, MAP_HEIGHT - 400, 250, 20))
        for i in range(4):
            self.platforms.append(pygame.Rect(400 + i * 500, MAP_HEIGHT - 600, 200, 20))
        for i in range(4):
            self.platforms.append(pygame.Rect(200 + i * 500, MAP_HEIGHT - 800, 200, 20))
        for i in range(3):
            self.platforms.append(pygame.Rect(500 + i * 500, MAP_HEIGHT - 1000, 200, 20))
    
    def rotate_platforms_phase2(self):
        """Rotate platforms to vertical orientation for Phase 2"""
        rotated_platforms = []
        
        # Keep ground platform
        rotated_platforms.append(self.platforms[0])
        
        # Rotate other platforms to vertical (swap width/height)
        for platform in self.platforms[1:]:
            # Convert horizontal platform to vertical
            new_x = platform.x + platform.width // 2 - 10  # Center and make narrow
            new_y = platform.y - 100  # Extend upward
            new_width = 20  # Narrow vertical platform
            new_height = platform.width  # Original width becomes height
            
            rotated_platforms.append(pygame.Rect(new_x, new_y, new_width, new_height))
        
        self.platforms = rotated_platforms
    
    def load_meta_progression(self):
        """Load ONLY meta progression - never runtime state"""
        result = self.save_manager.load_meta_progression(self.shop.items)
        if result:
            meta_data, unlocked_classes, mastery_unlocks = result
            self.currency = meta_data.get('total_credits', 0)
            self.unlocked_classes = unlocked_classes
            self.mastery_unlocks = mastery_unlocks
            self.selected_character = meta_data.get('last_selected_class', "Base")
            self.meta_quest_progress.update(meta_data.get('quest_progress', {}))
            self.menu.show_notification(f"Meta progression loaded! Credits: {self.currency}")
        else:
            # No save exists - start fresh
            self.currency = 0
    
    def save_meta_progression(self):
        """Save ONLY meta progression - never runtime state"""
        # Sync current player quest progress to meta
        if self.player:
            self.meta_quest_progress.update(self.player.quest_progress)

        if self.save_manager.save_meta_progression(self.currency, self.shop.items, self.unlocked_classes, self.meta_quest_progress, self.mastery_unlocks, self.selected_character):
            self.menu.show_notification("Progress saved!")
            return True
        else:
            self.menu.show_notification("Save failed!")
            return False
    
    def return_to_menu_run_lost(self):
        """Return to menu - destroys current run permanently"""
        # Save meta progression before destroying run
        self.save_meta_progression()
        
        # Destroy ALL runtime data
        self.player = None
        self.boss = None
        self.projectiles = []
        self.minions = []
        self.fire_zones = []
        self.lasers = []
        self.temp_walls = []
        self.healing_orbs = []
        self.total_damage_dealt = 0
        
        # Return to menu
        self.state = GameState.MAIN_MENU
        self.menu.selected = 0
    
    def start_game(self):
        self.state = GameState.PLAYING
        
        # Get character stats
        char_stats = self.menu.character_stats[self.selected_character]
        base_hp = char_stats['base_hp']
        hp_bonus = char_stats['hp_bonus']
        
        # Get equipped stats from shop (additional bonuses)
        shop_hp, base_damage, weapon_type = self.shop.get_equipped_stats()
        
        # Total HP = Base + Class Bonus + Shop Bonus
        total_hp = base_hp + hp_bonus + shop_hp
        
        self.player = Player(total_hp, base_damage, weapon_type)
        # Store class info in player for passives/buffs if needed
        self.player.character_class = self.selected_character
        self.player.game = self  # Reference to game for quest tracking
        self.player.quest_progress.update(self.meta_quest_progress)
        
        self.boss = Boss()
        self.miniboss_manager = MiniBossManager()
        self.miniboss_phase_completed = False
        self.projectiles = []
        self.minions = []
        self.fire_zones = []
        self.lasers = []
        self.temp_walls = []
        self.healing_orbs = []
        self.orb_spawn_timer = 0
        self.laser_spawn_queue = []
        self.godmode = False
        self.boss_invincible = False
        self.paused = False
    
    def load_game(self):
        save_data = self.save_manager.load_game(self.shop.items)
        if save_data:
            self.currency = save_data['currency']
            self.game_progress = save_data['game_progress']
            
            # Get equipped stats
            max_hp, base_damage, weapon_type = self.shop.get_equipped_stats()
            
            self.player = Player(max_hp, base_damage, weapon_type)
            self.player.x = save_data['player']['x']
            self.player.y = save_data['player']['y']
            self.player.hp = save_data['player']['hp']
            
            self.boss = Boss()
            self.projectiles = []
            self.minions = []
            self.fire_zones = []
            self.lasers = []
            self.temp_walls = []
            self.healing_orbs = []
            
            self.state = GameState.PLAYING
            self.menu.show_notification("Game loaded!")
        else:
            self.menu.show_notification("No save file found!")
    
    def save_game(self):
        if self.player and self.boss:
            if self.save_manager.save_game(self.player, self.currency, self.game_progress, self.shop.items):
                self.menu.show_notification("Game saved!")
            else:
                self.menu.show_notification("Save failed!")
    
    def check_admin_login(self):
        correct_username = "admin"
        correct_password = "060904A@"
        
        if self.admin_username == correct_username and self.admin_password == correct_password:
            self.admin_authenticated = True
            self.admin_login_mode = False
            self.admin_panel_active = True
            self.admin_history.append("=== LOGIN SUCCESSFUL ===")
            self.admin_history.append("Welcome, Admin!")
            self.admin_history.append("Type 'help' for commands")
            self.admin_username = ""
            self.admin_password = ""
        else:
            self.admin_login_attempts += 1
            self.admin_history.append(f"LOGIN FAILED - Attempt {self.admin_login_attempts}/3")
            self.admin_username = ""
            self.admin_password = ""
            self.admin_input_field = "username"
            
            if self.admin_login_attempts >= 3:
                self.admin_history.append("TOO MANY FAILED ATTEMPTS")
                self.admin_login_mode = False
                self.admin_login_attempts = 0
    
    def execute_admin_command(self, cmd):
        parts = cmd.lower().strip().split()
        if not parts:
            return
        
        try:
            # Player commands
            if parts[0] == "godmode":
                self.godmode = parts[1] == "on" if len(parts) > 1 else not self.godmode
                self.admin_history.append(f"Godmode: {'ON' if self.godmode else 'OFF'}")
            
            elif parts[0] == "set" and len(parts) >= 3:
                if parts[1] == "hp" and self.player:
                    self.player.hp = int(parts[2])
                    self.admin_history.append(f"Player HP set to {parts[2]}")
                elif parts[1] == "max_hp" and self.player:
                    self.player.max_hp = int(parts[2])
                    self.admin_history.append(f"Player Max HP set to {parts[2]}")
                elif parts[1] == "speed" and self.player:
                    self.player.speed = float(parts[2])
                    self.admin_history.append(f"Player speed set to {parts[2]}")
                elif parts[1] == "jump" and self.player:
                    self.player.jump_power = float(parts[2])
                    self.admin_history.append(f"Jump power set to {parts[2]}")
                elif parts[1] == "dash" and self.player:
                    self.player.dash_speed = float(parts[2])
                    self.admin_history.append(f"Dash speed set to {parts[2]}")
            
            elif parts[0] == "tp" and len(parts) >= 3 and self.player:
                self.player.x = float(parts[1])
                self.player.y = float(parts[2])
                self.admin_history.append(f"Player teleported to ({parts[1]}, {parts[2]})")
            
            elif parts[0] == "heal" and self.player:
                self.player.hp = self.player.max_hp
                self.admin_history.append("Player healed to full")
            
            elif parts[0] == "reset_player":
                max_hp, base_damage, weapon_type = self.shop.get_equipped_stats()
                self.player = Player(max_hp, base_damage, weapon_type)
                self.admin_history.append("Player reset")
            
            elif parts[0] == "parry" and self.player:
                self.player.parrying = parts[1] == "on" if len(parts) > 1 else not self.player.parrying
                self.admin_history.append(f"Parry: {'ON' if self.player.parrying else 'OFF'}")
            
            elif parts[0] == "charge" and len(parts) >= 2 and self.player:
                self.player.charge_percent = float(parts[1])
                self.admin_history.append(f"Charge set to {parts[1]}%")
            
            elif parts[0] == "basic_attack" and self.player:
                self.player.attack_cooldown = 0
                self.player.basic_attack()
                self.admin_history.append("Basic attack executed")
            
            elif parts[0] == "release_charge" and self.player:
                attack_data = self.player.release_charged_attack()
                if attack_data:
                    self.admin_history.append(f"Charged attack released ({attack_data['damage']} dmg)")
            
            # Boss commands
            elif parts[0] == "kill" and len(parts) >= 2 and parts[1] == "boss" and self.boss:
                self.boss.hp = 0
                self.admin_history.append("Boss killed")
            
            elif parts[0] == "boss_hp" and len(parts) >= 2 and self.boss:
                self.boss.hp = int(parts[1])
                self.admin_history.append(f"Boss HP set to {parts[1]}")
            
            elif parts[0] == "boss" and len(parts) >= 2:
                if parts[1] == "phase1" and self.boss:
                    self.boss.phase = 1
                    self.boss.fireball_cooldown_max = self.boss.fireball_cooldown_max_base
                    self.boss.laser_cooldown_max = self.boss.laser_cooldown_max_base
                    self.boss.shockwave_cooldown_max = self.boss.shockwave_cooldown_max_base
                    self.boss.minion_cooldown_max = self.boss.minion_cooldown_max_base
                    self.platform_hazard_active = False
                    self.platforms_visible = True
                    self.setup_arena()  # Reset platforms to horizontal
                    self.admin_history.append("Boss forced to Phase 1")
                elif parts[1] == "phase2" and self.boss:
                    if self.boss.phase != 2:
                        self.boss.phase = 2
                        self.boss.fireball_cooldown_max = self.boss.fireball_cooldown_max_base // 3
                        self.boss.laser_cooldown_max = self.boss.laser_cooldown_max_base // 3
                        self.boss.shockwave_cooldown_max = self.boss.shockwave_cooldown_max_base // 3
                        self.boss.minion_cooldown_max = self.boss.minion_cooldown_max_base // 3
                        self.rotate_platforms_phase2()
                        self.platform_hazard_active = True
                        self.platform_disappear_timer = 1200
                        self.admin_history.append("Boss forced to Phase 2")
                elif parts[1] == "reset":
                    self.boss = Boss()
                    self.platform_hazard_active = False
                    self.platforms_visible = True
                    self.setup_arena()
                    self.admin_history.append("Boss reset")
                elif parts[1] == "teleport" and len(parts) >= 4:
                    self.boss.x = float(parts[2])
                    self.boss.y = float(parts[3])
                    self.admin_history.append(f"Boss teleported to ({parts[2]}, {parts[3]})")
                elif parts[1] == "invincible":
                    self.boss_invincible = parts[2] == "on" if len(parts) > 2 else not self.boss_invincible
                    self.admin_history.append(f"Boss invincible: {'ON' if self.boss_invincible else 'OFF'}")
                elif parts[1] == "fireball" and self.boss:
                    for i in range(5):
                        x = self.boss.x + self.boss.width // 2
                        y = self.boss.y + self.boss.height
                        vel_x = random.uniform(-4, 4)
                        vel_y = random.uniform(-3, 1)
                        self.projectiles.append(Projectile(x, y, vel_x, vel_y, 10, 'fireball'))
                    self.admin_history.append("Boss fireball attack spawned")
                elif parts[1] == "laser" and self.boss and self.player:
                    laser_x = self.player.x + self.player.width // 2 - 25
                    self.lasers.append({'rect': pygame.Rect(laser_x, 0, 50, MAP_HEIGHT), 'timer': 30, 'fire_frame': 10})
                    self.admin_history.append("Boss laser spawned")
                elif parts[1] == "shockwave" and self.boss and self.player:
                    direction = 1 if self.player.x > self.boss.x else -1
                    self.projectiles.append(Projectile(self.boss.x + self.boss.width // 2, self.boss.y + self.boss.height, direction * 8, 2, 20, 'shockwave'))
                    self.admin_history.append("Boss shockwave spawned")
                elif parts[1] == "summon_minions" and self.boss:
                    count = int(parts[2]) if len(parts) > 2 else 3
                    for i in range(count):
                        spawn_x = self.boss.x + random.randint(-100, 100)
                        self.minions.append(Minion(spawn_x, self.boss.y + 200))
                    self.admin_history.append(f"Spawned {count} minions")
                elif parts[1] == "cooldowns" and len(parts) >= 3 and parts[2] == "reset" and self.boss:
                    self.boss.fireball_cooldown = 0
                    self.boss.laser_cooldown = 0
                    self.boss.shockwave_cooldown = 0
                    self.boss.minion_cooldown = 0
                    self.admin_history.append("Boss cooldowns reset")
                elif parts[1] == "phase" and len(parts) >= 3:
                    phase = int(parts[2])
                    if phase == 1:
                        self.boss.phase = 1
                        self.boss.fireball_cooldown_max = self.boss.fireball_cooldown_max_base
                        self.boss.laser_cooldown_max = self.boss.laser_cooldown_max_base
                        self.boss.shockwave_cooldown_max = self.boss.shockwave_cooldown_max_base
                        self.boss.minion_cooldown_max = self.boss.minion_cooldown_max_base
                        self.platform_hazard_active = False
                        self.platforms_visible = True
                        self.setup_arena()
                    elif phase == 2:
                        self.boss.phase = 2
                        self.boss.fireball_cooldown_max = self.boss.fireball_cooldown_max_base // 3
                        self.boss.laser_cooldown_max = self.boss.laser_cooldown_max_base // 3
                        self.boss.shockwave_cooldown_max = self.boss.shockwave_cooldown_max_base // 3
                        self.boss.minion_cooldown_max = self.boss.minion_cooldown_max_base // 3
                        self.rotate_platforms_phase2()
                        self.platform_hazard_active = True
                        self.platform_disappear_timer = 1200
                    self.admin_history.append(f"Boss phase set to {phase}")
            
            # Spawn commands
            elif parts[0] == "spawn":
                if parts[1] == "lava" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.fire_zones.append({'rect': pygame.Rect(x - 40, y - 40, 80, 40), 'timer': 900})
                    self.admin_history.append(f"Lava spawned at ({x}, {y})")
                elif parts[1] == "fireball" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.projectiles.append(Projectile(x, y, 0, 5, 10, 'fireball'))
                    self.admin_history.append(f"Fireball spawned at ({x}, {y})")
                elif parts[1] == "shockwave" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.projectiles.append(Projectile(x, y, 8, 0, 20, 'shockwave'))
                    self.admin_history.append(f"Shockwave spawned")
                elif parts[1] == "charged_attack" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.projectiles.append(Projectile(x, y, 5, 0, 10, 'charged_attack'))
                    self.admin_history.append(f"Charged attack spawned")
                elif parts[1] == "minion" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.minions.append(Minion(x, y))
                    self.admin_history.append(f"Minion spawned at ({x}, {y})")
                elif parts[1] == "orb" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.healing_orbs.append(HealingOrb(x, y))
                    self.admin_history.append(f"Healing orb spawned at ({x}, {y})")
                elif parts[1] == "temp_wall" and len(parts) >= 4:
                    x, y = float(parts[2]), float(parts[3])
                    self.temp_walls.append({'rect': pygame.Rect(x, y, 20, 400), 'timer': 480})
                    self.admin_history.append(f"Temp wall spawned at ({x}, {y})")
            
            # Clear commands
            elif parts[0] == "clear":
                if parts[1] == "projectiles":
                    self.projectiles.clear()
                    self.admin_history.append("All projectiles cleared")
                elif parts[1] == "minions":
                    self.minions.clear()
                    self.admin_history.append("All minions cleared")
                elif parts[1] == "fire":
                    self.fire_zones.clear()
                    self.admin_history.append("All fire zones cleared")
                elif parts[1] == "orbs":
                    self.healing_orbs.clear()
                    self.admin_history.append("All orbs cleared")
            
            # Game state commands
            elif parts[0] == "win":
                self.state = GameState.VICTORY
                self.admin_history.append("Victory triggered")
            
            elif parts[0] == "lose":
                self.state = GameState.GAME_OVER
                self.admin_history.append("Game over triggered")
            
            elif parts[0] == "restart":
                self.start_game()
                self.admin_history.append("Game restarted")
            
            elif parts[0] == "pause":
                self.paused = parts[1] == "on" if len(parts) > 1 else not self.paused
                self.admin_history.append(f"Pause: {'ON' if self.paused else 'OFF'}")
            
            # Camera commands
            elif parts[0] == "camera":
                if len(parts) >= 3:
                    self.camera_x = float(parts[1])
                    self.camera_y = float(parts[2])
                    self.admin_history.append(f"Camera set to ({parts[1]}, {parts[2]})")
                elif len(parts) >= 2 and parts[1] == "follow":
                    self.camera_follow = parts[2] == "on" if len(parts) > 2 else not self.camera_follow
                    self.admin_history.append(f"Camera follow: {'ON' if self.camera_follow else 'OFF'}")
            
            # Debug mode
            elif parts[0] == "debug":
                self.debug_mode = parts[1] == "on" if len(parts) > 1 else not self.debug_mode
                self.admin_history.append(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
            
            # Currency commands
            elif parts[0] == "currency" and len(parts) >= 2:
                self.currency = int(parts[1])
                self.admin_history.append(f"Currency set to {parts[1]}")
            
            elif parts[0] == "give" and len(parts) >= 2:
                amount = int(parts[1])
                self.currency += amount
                self.save_meta_progression()  # Auto-save after admin currency grant
                self.admin_history.append(f"Gave {amount} currency (Total: {self.currency})")
            
            # Save/Load
            elif parts[0] == "save":
                self.save_meta_progression()
                self.admin_history.append("Meta progression saved via admin")
            
            elif parts[0] == "reset_save":
                if self.save_manager.delete_save():
                    self.currency = 0
                    for item in self.shop.items:
                        item.owned = False
                        item.equipped = False
                    self.admin_history.append("Save file deleted - meta progression reset")
                else:
                    self.admin_history.append("Failed to delete save")
            
            elif parts[0] == "reset":
                # Full reset: delete save, reset currency, reset items, reset current run
                if self.save_manager.delete_save():
                    self.currency = 0
                    for item in self.shop.items:
                        item.owned = False
                        item.equipped = False
                    # Reset current run if in game
                    if self.player and self.boss:
                        self.start_game()
                    self.admin_history.append("FULL RESET - Save deleted, currency cleared, run restarted")
                else:
                    self.admin_history.append("Failed to delete save file")
            
            elif parts[0] == "unlock_all":
                for item in self.shop.items:
                    item.owned = True
                self.save_meta_progression()  # Auto-save after unlock
                self.admin_history.append("All items unlocked and saved")
            
            elif parts[0] == "boss_phase2" and self.boss:
                if self.boss.phase != 2:
                    self.boss.phase = 2
                    self.boss.fireball_cooldown_max = self.boss.fireball_cooldown_max_base // 3
                    self.boss.laser_cooldown_max = self.boss.laser_cooldown_max_base // 3
                    self.boss.shockwave_cooldown_max = self.boss.shockwave_cooldown_max_base // 3
                    self.boss.minion_cooldown_max = self.boss.minion_cooldown_max_base // 3
                    self.rotate_platforms_phase2()
                    self.platform_hazard_active = True
                    self.platform_disappear_timer = 1200
                    self.admin_history.append("Boss Phase 2 activated!")
                else:
                    self.admin_history.append("Boss already in Phase 2")
            
            # Help command
            elif parts[0] == "help":
                self.admin_history.append("=== ADMIN COMMANDS ===")
                self.admin_history.append("PLAYER: godmode, set hp/max_hp/speed/jump/dash")
                self.admin_history.append("tp <x> <y>, heal, reset_player, parry, charge")
                self.admin_history.append("BOSS: kill boss, boss_hp, boss phase1/phase2")
                self.admin_history.append("boss reset, boss teleport, boss invincible")
                self.admin_history.append("boss fireball/laser/shockwave/summon_minions")
                self.admin_history.append("SPAWN: spawn lava/fireball/minion/orb/temp_wall")
                self.admin_history.append("CLEAR: clear projectiles/minions/fire/orbs")
                self.admin_history.append("GAME: win, lose, restart, pause")
                self.admin_history.append("CAMERA: camera <x> <y>, camera follow")
                self.admin_history.append("OTHER: currency, give, save, unlock_all")
                self.admin_history.append("reset - FULL RESET (save + currency + items + run)")
                self.admin_history.append("reset_save - Delete save file only, debug")
                self.admin_history.append("Type 'logout' to exit admin panel")
            
            elif parts[0] == "logout":
                self.admin_authenticated = False
                self.admin_panel_active = False
                self.admin_history.append("Logged out")
            
            else:
                self.admin_history.append(f"Unknown: {cmd}")
        
        except Exception as e:
            self.admin_history.append(f"Error: {str(e)}")
        
        if len(self.admin_history) > 20:
            self.admin_history = self.admin_history[-20:]
    
    def boss_ai(self):
        if not self.boss or not self.player:
            return
        
        # Don't attack during Phase 2 transition
        if self.boss.phase2_transition_active:
            return
            
        multiplier = 3 if self.boss.phase == 2 else 1
        
        if self.boss.fireball_cooldown == 0:
            for _ in range(multiplier):
                for i in range(5):
                    x = self.boss.x + self.boss.width // 2
                    y = self.boss.y + self.boss.height
                    vel_x = random.uniform(-4, 4)
                    vel_y = random.uniform(-3, 1)
                    self.projectiles.append(Projectile(x, y, vel_x, vel_y, 10, 'fireball'))
            self.boss.fireball_cooldown = self.boss.fireball_cooldown_max
        
        if self.boss.laser_cooldown == 0:
            base_timer, fire_frame = 30, 10
            if self.boss.phase == 1:
                laser_x = self.player.x + self.player.width // 2 - 25
                self.lasers.append({'rect': pygame.Rect(laser_x, 0, 50, MAP_HEIGHT), 'timer': base_timer, 'fire_frame': fire_frame})
            else:
                for i in range(3):
                    offset = random.randint(-100, 100)
                    laser_x = self.player.x + self.player.width // 2 - 25 + offset
                    laser = {'rect': pygame.Rect(laser_x, 0, 50, MAP_HEIGHT), 'timer': base_timer, 'fire_frame': fire_frame}
                    if i == 0:
                        self.lasers.append(laser)
                    else:
                        self.laser_spawn_queue.append({'laser': laser, 'delay': i * 6})
            self.boss.laser_cooldown = self.boss.laser_cooldown_max
        
        if self.boss.shockwave_cooldown == 0:
            for _ in range(multiplier):
                direction = 1 if self.player.x > self.boss.x else -1
                self.projectiles.append(Projectile(self.boss.x + self.boss.width // 2, self.boss.y + self.boss.height, direction * 8, 2, 20, 'shockwave'))
            self.boss.shockwave_cooldown = self.boss.shockwave_cooldown_max
        
        if self.boss.minion_cooldown == 0:
            for _ in range(multiplier):
                for i in range(3):
                    spawn_x = self.boss.x + random.randint(-100, 100)
                    self.minions.append(Minion(spawn_x, self.boss.y + 200))
            self.boss.minion_cooldown = self.boss.minion_cooldown_max
    
    def update(self):
        self.menu.update_notification()
        
        if self.paused or self.state != GameState.PLAYING:
            return
        
        # Slow down gameplay during boss Phase 2 transition
        if self.boss and self.boss.phase2_transition_active:
            # Update boss transition animation
            self.boss.update(self)
            
            # Trigger platform rotation on transition start
            if self.boss.phase2_transition_timer == 1:
                self.rotate_platforms_phase2()
                self.platform_hazard_active = True
                self.platform_disappear_timer = 1200
            
            return  # Pause other game logic during transition
            
        if self.state == GameState.PLAYING and self.player and self.boss:
            mouse_pos = pygame.mouse.get_pos()
            self.player.update(self.platforms, self.walls, self.temp_walls, self.fire_zones, mouse_pos, self.camera_x, self.camera_y, self)
            
            if self.godmode and self.player.hp < self.player.max_hp:
                self.player.hp = self.player.max_hp
            
            miniboss_active = hasattr(self, 'miniboss_manager') and self.miniboss_manager.active
            
            if hasattr(self, 'miniboss_manager'):
                if self.miniboss_manager.active:
                    self.miniboss_manager.update(self.player, self.projectiles, self.minions)
                    self.miniboss_manager.check_damage_to_player(self.player)
                    
                    if not self.miniboss_manager.active and not self.miniboss_phase_completed:
                        self.miniboss_phase_completed = True
                elif not self.miniboss_phase_completed and self.boss.hp <= self.boss.max_hp // 2:
                    self.miniboss_manager.active = True
                    miniboss_active = True
                    # Reset boss position for Phase 2 when they return
                    self.boss.x = MAP_WIDTH // 2
                    self.boss.y = 100
                    self.boss.visual_x = self.boss.x
                    self.boss.visual_y = self.boss.y
            
            if not miniboss_active:
                self.boss.update(self)
                self.boss_ai()
            
            for proj in self.projectiles[:]:
                proj.update()
                proj_rect = pygame.Rect(proj.x - proj.radius, proj.y - proj.radius, proj.radius * 2, proj.radius * 2)
                
                if proj.type == 'charged_attack':
                    boss_rect = pygame.Rect(self.boss.x, self.boss.y, self.boss.width, self.boss.height)
                    if proj_rect.colliderect(boss_rect) and not miniboss_active:
                        if not self.boss_invincible:
                            damage = int(proj.damage)
                            self.boss.take_damage(damage)
                            self.player.on_deal_damage(damage)
                            self.total_damage_dealt += damage
                            
                            # Award currency: 2 credits per 10 damage
                            credits_earned = (self.total_damage_dealt // 10) * 2
                            previous_credits = ((self.total_damage_dealt - damage) // 10) * 2
                            new_credits = credits_earned - previous_credits
                            if new_credits > 0:
                                self.currency += new_credits
                        self.projectiles.remove(proj)
                        continue
                    
                    if hasattr(self, 'miniboss_manager') and self.miniboss_manager.active:
                        for mboss in [self.miniboss_manager.left_boss, self.miniboss_manager.right_boss]:
                            if mboss:
                                mboss_rect = pygame.Rect(mboss.x, mboss.y, mboss.width, mboss.height)
                                if proj_rect.colliderect(mboss_rect):
                                    damage = int(proj.damage)
                                    mboss.take_damage(damage)
                                    self.player.on_deal_damage(damage)
                                    self.total_damage_dealt += damage
                                    
                                    # Award currency: 2 credits per 10 damage
                                    credits_earned = (self.total_damage_dealt // 10) * 2
                                    previous_credits = ((self.total_damage_dealt - damage) // 10) * 2
                                    new_credits = credits_earned - previous_credits
                                    if new_credits > 0:
                                        self.currency += new_credits
                                    
                                    self.projectiles.remove(proj)
                                    break
                    
                    if proj.x < 0 or proj.x > MAP_WIDTH or proj.y < 0 or proj.y > MAP_HEIGHT:
                        self.projectiles.remove(proj)
                        continue
                
                player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
                if proj_rect.colliderect(player_rect) and not self.player.invulnerable and proj.type != 'charged_attack' and not self.godmode:
                    damage_type = "magic" if proj.type in ['fireball', 'laser'] else "normal"
                    self.player.take_damage(proj.damage, damage_type, self.boss)
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    if proj.type == 'fireball':
                        self.fire_zones.append({'rect': pygame.Rect(proj.x - 40, proj.y - 20, 80, 40), 'timer': 900})
                elif proj.y > MAP_HEIGHT or proj.x < 0 or proj.x > MAP_WIDTH:
                    if proj.type == 'fireball':
                        landed = False
                        fireball_rect = pygame.Rect(proj.x - 40, proj.y - 20, 80, 40)
                        for platform in self.platforms:
                            if fireball_rect.colliderect(platform):
                                self.fire_zones.append({'rect': pygame.Rect(proj.x - 40, platform.top - 40, 80, 40), 'timer': 900})
                                landed = True
                                break
                        if not landed and proj.y > MAP_HEIGHT - 100:
                            self.fire_zones.append({'rect': pygame.Rect(proj.x - 40, MAP_HEIGHT - 90, 80, 40), 'timer': 900})
                    if proj.type != 'charged_attack' and proj in self.projectiles:
                        self.projectiles.remove(proj)
            
            for minion in self.minions[:]:
                minion.update(self.player, self.platforms)
                minion_rect = pygame.Rect(minion.x, minion.y, minion.width, minion.height)
                player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
                if minion_rect.colliderect(player_rect) and not self.player.invulnerable and not self.godmode:
                    self.player.take_damage(5, "normal", minion)
                    self.minions.remove(minion)
            
            for fire in self.fire_zones[:]:
                fire['timer'] -= 1
                if fire['timer'] <= 0:
                    self.fire_zones.remove(fire)
            
            for laser in self.lasers[:]:
                laser['timer'] -= 1
                if laser['timer'] <= 0:
                    self.lasers.remove(laser)
                elif laser['timer'] == laser['fire_frame']:
                    player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
                    if laser['rect'].colliderect(player_rect) and not self.player.invulnerable and not self.godmode:
                        self.player.take_damage(30, "magic", self.boss)
            
            for wall in self.temp_walls[:]:
                wall['timer'] -= 1
                if wall['timer'] <= 0:
                    self.temp_walls.remove(wall)
            
            if random.randint(1, 300) == 1:
                self.temp_walls.append({'rect': pygame.Rect(random.randint(400, MAP_WIDTH - 400), random.randint(400, MAP_HEIGHT - 400), 20, 400), 'timer': 480})
            
            self.orb_spawn_timer += 1
            if len(self.healing_orbs) < 3 and self.orb_spawn_timer >= 600:
                self.healing_orbs.append(HealingOrb(random.randint(200, MAP_WIDTH - 200), random.randint(300, MAP_HEIGHT - 300)))
                self.orb_spawn_timer = 0
            
            for orb in self.healing_orbs[:]:
                orb.update()
                if pygame.Rect(orb.x - orb.radius, orb.y - orb.radius, orb.radius * 2, orb.radius * 2).colliderect(pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)):
                    self.player.hp = min(self.player.hp + orb.heal_amount, self.player.max_hp)
                    self.healing_orbs.remove(orb)
                    self.orb_spawn_timer = 0
            
            for laser_data in self.laser_spawn_queue[:]:
                laser_data['delay'] -= 1
                if laser_data['delay'] <= 0:
                    self.lasers.append(laser_data['laser'])
                    self.laser_spawn_queue.remove(laser_data)
            
            # Boss Phase 2 platform hazard
            if self.platform_hazard_active and self.boss and self.boss.phase == 2:
                self.platform_disappear_timer -= 1
                
                if self.platform_disappear_timer <= 0:
                    # Toggle platform visibility
                    self.platforms_visible = not self.platforms_visible
                    if self.platforms_visible:
                        self.platform_disappear_timer = 1200
                    else:
                        self.platform_disappear_timer = 300
            
            # Quest elements
            # Crystal spawning for Mage quest
            if random.randint(1, 1000) == 1:
                crystal_x = random.randint(200, MAP_WIDTH - 200)
                crystal_y = random.randint(300, MAP_HEIGHT - 300)
                self.crystals.append({'x': crystal_x, 'y': crystal_y, 'radius': 15})

            # Crystal collection
            player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
            for crystal in self.crystals[:]:
                crystal_rect = pygame.Rect(crystal['x'] - crystal['radius'], crystal['y'] - crystal['radius'], crystal['radius'] * 2, crystal['radius'] * 2)
                if player_rect.colliderect(crystal_rect):
                    self.player.quest_progress['mage_crystals'] += 1
                    self.crystals.remove(crystal)

            # Laser attack timer for Rogue quest
            if self.boss and self.boss.laser_cooldown == 0:
                self.laser_attack_timer = 120
                self.player.laser_damage_taken = False

            if self.laser_attack_timer > 0:
                self.laser_attack_timer -= 1
                if self.laser_attack_timer == 0 and not self.player.laser_damage_taken:
                    self.player.consecutive_laser_avoids += 1
                    self.player.quest_progress['rogue_laser_avoids'] = self.player.consecutive_laser_avoids
                elif self.player.laser_damage_taken:
                    self.player.consecutive_laser_avoids = 0
                    self.player.quest_progress['rogue_laser_avoids'] = 0

            # Check for class unlocks
            if self.player.quest_progress['warrior_damage'] >= 100 and 'Warrior' not in self.unlocked_classes:
                self.unlocked_classes.add('Warrior')
                self.save_meta_progression()
            if self.player.quest_progress['mage_crystals'] >= 5 and 'Mage' not in self.unlocked_classes:
                self.unlocked_classes.add('Mage')
                self.save_meta_progression()
            if self.player.quest_progress['archer_range_damage'] >= 100 and 'Archer' not in self.unlocked_classes:
                self.unlocked_classes.add('Archer')
                self.save_meta_progression()
            if self.player.quest_progress['rogue_laser_avoids'] >= 10 and 'Rogue' not in self.unlocked_classes:
                self.unlocked_classes.add('Rogue')
                self.save_meta_progression()
            if self.player.quest_progress['reaver_low_hp_damage'] >= 100 and 'Reaver' not in self.unlocked_classes:
                self.unlocked_classes.add('Reaver')
                self.save_meta_progression()

            # Check for mastery unlocks
            if self.player.quest_progress['warrior_parries'] >= 10 and 'Warrior' not in self.mastery_unlocks:
                self.mastery_unlocks.add('Warrior')
                self.menu.show_notification("WARRIOR MASTERED!")
                self.save_meta_progression()
            if self.player.quest_progress['mage_mana_spent'] >= 500 and 'Mage' not in self.mastery_unlocks:
                self.mastery_unlocks.add('Mage')
                self.menu.show_notification("MAGE MASTERED!")
                self.save_meta_progression()
            if self.player.quest_progress['archer_crit_hits'] >= 20 and 'Archer' not in self.mastery_unlocks:
                self.mastery_unlocks.add('Archer')
                self.menu.show_notification("ARCHER MASTERED!")
                self.save_meta_progression()
            if self.player.quest_progress['rogue_backstabs'] >= 50 and 'Rogue' not in self.mastery_unlocks:
                self.mastery_unlocks.add('Rogue')
                self.menu.show_notification("ROGUE MASTERED!")
                self.save_meta_progression()
            if self.player.quest_progress['reaver_hp_siphoned'] >= 200 and 'Reaver' not in self.mastery_unlocks:
                self.mastery_unlocks.add('Reaver')
                self.menu.show_notification("REAVER MASTERED!")
                self.save_meta_progression()

            # Reaver Crimson Aura check
            if self.player.character_class == "Reaver":
                dist_to_boss = math.hypot(self.player.x - self.boss.x, self.player.y - self.boss.y)
                if dist_to_boss < 300:
                    self.player.buffs["crimson_aura"] = 2
                else:
                    for minion in self.minions:
                        if math.hypot(self.player.x - minion.x, self.player.y - minion.y) < 200:
                            self.player.buffs["crimson_aura"] = 2
                            break
            
            target_x = self.player.x - SCREEN_WIDTH // 2
            target_y = self.player.y - SCREEN_HEIGHT // 2
            if self.camera_follow:
                self.camera_x += (target_x - self.camera_x) * 0.1
                self.camera_y += (target_y - self.camera_y) * 0.1
            self.camera_x = max(0, min(self.camera_x, MAP_WIDTH - SCREEN_WIDTH))
            self.camera_y = max(0, min(self.camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
            
            if self.player.hp <= 0:
                self.state = GameState.GAME_OVER
                # Auto-save meta progression on game over
                self.save_meta_progression()
            elif self.boss.hp <= 0:
                self.state = GameState.VICTORY
                self.currency += 1000  # Victory reward
                # Auto-save meta progression on victory
                self.save_meta_progression()
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                # F5 - Instant quit
                if event.key == pygame.K_F5:
                    self.running = False
                    return
                
                # ESC - Context-dependent
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.state = GameState.PAUSED
                        self.menu.selected = 0
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.PLAYING
                    elif self.state == GameState.SHOP:
                        self.state = GameState.MAIN_MENU
                        self.menu.selected = 0
                    elif self.state == GameState.SETTINGS:
                        self.state = GameState.MAIN_MENU
                        self.menu.selected = 0
                    elif self.state == GameState.CHARACTER_SELECT:
                        self.state = GameState.MAIN_MENU
                        self.menu.selected = 0
                    elif self.state == GameState.QUEST_MENU:
                        if self.menu.quest_view_state == 1:
                            self.menu.quest_view_state = 0
                        else:
                            self.state = self.last_state
                    elif self.admin_login_mode:
                        self.admin_login_mode = False
                    elif self.admin_panel_active:
                        self.admin_panel_active = False
                    return
                
                # F2 - Admin panel
                if event.key == pygame.K_F2:
                    if not self.admin_authenticated and not self.admin_login_mode:
                        self.admin_login_mode = True
                        self.admin_username = ""
                        self.admin_password = ""
                        self.admin_input_field = "username"
                        self.admin_history.append("=== ADMIN LOGIN ===")
                    elif self.admin_authenticated:
                        self.admin_panel_active = not self.admin_panel_active
                    return
                
                # Admin login
                if self.admin_login_mode:
                    if event.key == pygame.K_RETURN:
                        if self.admin_input_field == "username":
                            self.admin_input_field = "password"
                        elif self.admin_input_field == "password":
                            self.check_admin_login()
                    elif event.key == pygame.K_BACKSPACE:
                        if self.admin_input_field == "username":
                            self.admin_username = self.admin_username[:-1]
                        else:
                            self.admin_password = self.admin_password[:-1]
                    elif event.unicode:
                        if self.admin_input_field == "username" and len(self.admin_username) < 20:
                            self.admin_username += event.unicode
                        elif self.admin_input_field == "password" and len(self.admin_password) < 20:
                            self.admin_password += event.unicode
                    return
                
                # Admin panel commands
                if self.admin_panel_active and self.admin_authenticated:
                    if event.key == pygame.K_RETURN:
                        if self.admin_input.strip():
                            self.execute_admin_command(self.admin_input)
                            self.admin_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.admin_input = self.admin_input[:-1]
                    elif event.unicode and len(self.admin_input) < 50:
                        self.admin_input += event.unicode
                    return
                
                # Main Menu
                if self.state == GameState.MAIN_MENU:
                    if event.key in [pygame.K_w, pygame.K_s]:
                        direction = -1 if event.key == pygame.K_w else 1
                        self.menu.navigate(direction, self.state)
                    elif event.key == pygame.K_RETURN:
                        option = self.menu.main_options[self.menu.selected]
                        if option == "Start Game":
                            self.state = GameState.CHARACTER_SELECT
                            self.menu.selected = 0
                        elif option == "Shop":
                            self.state = GameState.SHOP
                            self.shop.selected_index = 0
                        elif option == "Quests":
                            self.last_state = self.state
                            self.state = GameState.QUEST_MENU
                            self.menu.quest_view_state = 0
                            self.menu.selected = 0
                        elif option == "Settings":
                            self.state = GameState.SETTINGS
                            self.menu.selected = 0
                        elif option == "Exit (F5)":
                            self.running = False
                
                # Character Selection
                elif self.state == GameState.CHARACTER_SELECT:
                    available_classes = ["Base"] + [cls for cls in self.menu.character_options if cls in self.unlocked_classes]
                    if event.key in [pygame.K_w, pygame.K_s, pygame.K_UP, pygame.K_DOWN]:
                        direction = -1 if event.key in [pygame.K_w, pygame.K_UP] else 1
                        self.menu.selected = (self.menu.selected + direction) % len(available_classes)
                    elif event.key == pygame.K_RETURN:
                        self.selected_character = available_classes[self.menu.selected]
                        self.start_game()
                
                # Pause Menu
                elif self.state == GameState.PAUSED:
                    if event.key in [pygame.K_w, pygame.K_s]:
                        direction = -1 if event.key == pygame.K_w else 1
                        self.menu.navigate(direction, self.state)
                    elif event.key == pygame.K_RETURN:
                        option = self.menu.pause_options[self.menu.selected]
                        if option == "Return to Menu (Run Lost)":
                            self.return_to_menu_run_lost()
                        elif option == "Quit Game (F5)":
                            self.running = False
                
                # Shop
                elif self.state == GameState.SHOP:
                    if event.key == pygame.K_w:
                        self.shop.navigate(-1)
                    elif event.key == pygame.K_s:
                        self.shop.navigate(1)
                    elif event.key == pygame.K_b:
                        self.currency, msg = self.shop.buy_item(self.currency)
                        self.menu.show_notification(msg)
                        # Auto-save after purchase
                        self.save_meta_progression()
                    elif event.key == pygame.K_e:
                        msg = self.shop.equip_item()
                        if msg:
                            self.menu.show_notification(msg)
                            # Auto-save after equip change
                            self.save_meta_progression()
                
                # Settings
                elif self.state == GameState.SETTINGS:
                    if event.key in [pygame.K_UP, pygame.K_DOWN]:
                        direction = -1 if event.key == pygame.K_UP else 1
                        self.menu.navigate(direction, self.state)
                    elif event.key in [pygame.K_LEFT, pygame.K_RIGHT]:
                        if self.menu.selected == 0:  # Volume
                            self.menu.volume = max(0, min(100, self.menu.volume + (10 if event.key == pygame.K_RIGHT else -10)))
                            self.menu.settings_options[0] = f"Volume: {self.menu.volume}%"
                        elif self.menu.selected == 1:  # Speed
                            speeds = [0.5, 1.0, 1.5, 2.0]
                            names = ["Slow", "Normal", "Fast", "Very Fast"]
                            idx = speeds.index(self.menu.game_speed)
                            if event.key == pygame.K_RIGHT:
                                idx = min(len(speeds) - 1, idx + 1)
                            else:
                                idx = max(0, idx - 1)
                            self.menu.game_speed = speeds[idx]
                            self.menu.settings_options[1] = f"Speed: {names[idx]}"
                    elif event.key == pygame.K_RETURN:
                        if self.menu.selected == 2:  # Back
                            self.state = GameState.MAIN_MENU
                            self.menu.selected = 0
                
                # Game Over / Victory
                elif self.state in [GameState.GAME_OVER, GameState.VICTORY]:
                    if event.key == pygame.K_RETURN:
                        # Save meta progression before returning to menu
                        self.save_meta_progression()
                        self.state = GameState.MAIN_MENU
                        self.menu.selected = 0
                
                # Gameplay controls
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_SPACE:
                        self.player.jump()
                    elif event.key == pygame.K_a:
                        self.player.dash()
                    elif event.key == pygame.K_f:
                        self.player.parrying = True
                    elif event.key == pygame.K_w:
                        self.player.activate_buff(1)
                    elif event.key == pygame.K_c:
                        self.player.activate_buff(2)
                    elif event.key == pygame.K_x:
                        self.last_state = self.state
                        self.state = GameState.QUEST_MENU
                        self.menu.quest_view_state = 0
                        self.menu.selected = 0

                # Quest menu controls
                elif self.state == GameState.QUEST_MENU:
                    if event.key == pygame.K_x:
                        if self.menu.quest_view_state == 1:
                            self.menu.quest_view_state = 0
                        else:
                            self.state = self.last_state
                    
                    elif self.menu.quest_view_state == 0:  # Class selection
                        all_quest_classes = ["Warrior", "Mage", "Archer", "Rogue", "Reaver"]
                        if event.key in [pygame.K_w, pygame.K_UP]:
                            self.menu.selected = (self.menu.selected - 1) % len(all_quest_classes)
                        elif event.key in [pygame.K_s, pygame.K_DOWN]:
                            self.menu.selected = (self.menu.selected + 1) % len(all_quest_classes)
                        elif event.key == pygame.K_RETURN:
                            self.menu.selected_quest_class = all_quest_classes[self.menu.selected]
                            self.menu.quest_view_state = 1
                            self.menu.selected = 0
                    
                    elif self.menu.quest_view_state == 1:  # Quest list
                        if event.key == pygame.K_BACKSPACE:
                            self.menu.quest_view_state = 0
                            # Reset selection to the class we were just looking at
                            all_quest_classes = ["Warrior", "Mage", "Archer", "Rogue", "Reaver"]
                            if self.menu.selected_quest_class in all_quest_classes:
                                self.menu.selected = all_quest_classes.index(self.menu.selected_quest_class)
                            else:
                                self.menu.selected = 0
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_f and self.state == GameState.PLAYING and self.player:
                    self.player.parrying = False
            
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == GameState.PLAYING and self.player and self.boss:
                if event.button == 1:  # Left click - Basic attack
                    if self.player.basic_attack():
                        player_rect = pygame.Rect(self.player.x - 30, self.player.y - 30, self.player.width + 60, self.player.height + 60)
                        
                        miniboss_active = hasattr(self, 'miniboss_manager') and self.miniboss_manager.active
                        damage_dealt = 0
                        if not miniboss_active:
                            boss_rect = pygame.Rect(self.boss.x, self.boss.y, self.boss.width, self.boss.height)
                            if player_rect.colliderect(boss_rect) and not self.boss_invincible:
                                damage_dealt = self.player.calculate_damage(self.player.base_damage, "melee", self.boss)
                                self.boss.take_damage(damage_dealt)
                                self.player.on_deal_damage(damage_dealt)
                        else:
                            for mboss in [self.miniboss_manager.left_boss, self.miniboss_manager.right_boss]:
                                if mboss:
                                    mboss_rect = pygame.Rect(mboss.x, mboss.y, mboss.width, mboss.height)
                                    if player_rect.colliderect(mboss_rect):
                                        damage_dealt = self.player.calculate_damage(self.player.base_damage, "melee", mboss)
                                        mboss.take_damage(damage_dealt)
                                        self.player.on_deal_damage(damage_dealt)
                                        break
                        
                        if damage_dealt > 0:
                            self.total_damage_dealt += damage_dealt
                            # Award currency: 2 credits per 10 damage
                            credits_earned = (self.total_damage_dealt // 10) * 2
                            previous_credits = ((self.total_damage_dealt - damage_dealt) // 10) * 2
                            new_credits = credits_earned - previous_credits
                            if new_credits > 0:
                                self.currency += new_credits

                elif event.button == 3:  # Right click - Start charging
                    self.player.start_charging()
            
            if event.type == pygame.MOUSEBUTTONUP and self.state == GameState.PLAYING and self.player:
                if event.button == 3:  # Right click release - Charged attack
                    attack_data = self.player.release_charged_attack()
                    if attack_data and attack_data['charge'] >= 25:
                        speed = 15
                        vel_x = math.cos(attack_data['angle']) * speed
                        vel_y = math.sin(attack_data['angle']) * speed
                        start_x = self.player.x + self.player.width // 2
                        start_y = self.player.y + self.player.height // 2
                        self.projectiles.append(Projectile(start_x, start_y, vel_x, vel_y, attack_data['damage'], 'charged_attack'))
    
    def draw(self):
        self.screen.fill(BLACK)
        
        if self.state == GameState.MAIN_MENU:
            self.menu.draw_main_menu(self.screen)
        
        elif self.state == GameState.SHOP:
            self.menu.draw_shop(self.screen, self.shop, self.currency)
        
        elif self.state == GameState.SETTINGS:
            self.menu.draw_settings(self.screen)
        
        elif self.state == GameState.CHARACTER_SELECT:
            self.menu.draw_character_selection(self.screen, self.unlocked_classes)

        elif self.state == GameState.QUEST_MENU:
            # Sync if player exists to show real-time progress
            display_progress = self.meta_quest_progress
            if self.player:
                display_progress = self.player.quest_progress
            self.menu.draw_quest_menu(self.screen, self.quests, display_progress, self.unlocked_classes, self.mastery_unlocks)

        elif self.state == GameState.PLAYING:
            # Draw game arena
            for i, platform in enumerate(self.platforms):
                is_ground = (i == 0)
                # Only draw platforms if they're visible (Phase 2 mechanic), but ground always stays
                if self.platforms_visible or is_ground:
                    # Add subtle glow to platforms in Phase 2
                    if self.boss and self.boss.phase == 2:
                        glow_surf = pygame.Surface((platform.width + 10, platform.height + 10), pygame.SRCALPHA)
                        glow_surf.fill((*PURPLE, 30))
                        self.screen.blit(glow_surf, (platform.x - self.camera_x - 5, platform.y - self.camera_y - 5))
                    
                    pygame.draw.rect(self.screen, PURPLE, (platform.x - self.camera_x, platform.y - self.camera_y, platform.width, platform.height))
                elif not is_ground:
                    # Draw faded platforms when invisible with pulsing effect
                    pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 30) + 20
                    s = pygame.Surface((platform.width, platform.height))
                    s.set_alpha(pulse)
                    s.fill(PURPLE)
                    self.screen.blit(s, (platform.x - self.camera_x, platform.y - self.camera_y))
            
            for wall in self.temp_walls:
                # Animated temp walls
                alpha = int(200 + abs(math.sin(pygame.time.get_ticks() * 0.003)) * 55)
                wall_surf = pygame.Surface((wall['rect'].width, wall['rect'].height), pygame.SRCALPHA)
                wall_surf.fill((*DARK_PURPLE, alpha))
                self.screen.blit(wall_surf, (wall['rect'].x - self.camera_x, wall['rect'].y - self.camera_y))
            
            for fire in self.fire_zones:
                # Animated fire with flickering
                flicker = int(abs(math.sin(pygame.time.get_ticks() * 0.01)) * 20)
                fire_color = (255, flicker, 0)
                pygame.draw.rect(self.screen, fire_color, (fire['rect'].x - self.camera_x, fire['rect'].y - self.camera_y, fire['rect'].width, fire['rect'].height))
                
                # Add fire particles
                for i in range(3):
                    offset = random.randint(-10, 10)
                    particle_y = fire['rect'].y - random.randint(0, 20)
                    particle_size = random.randint(2, 5)
                    pygame.draw.circle(self.screen, ORANGE, (fire['rect'].x + fire['rect'].width // 2 + offset - self.camera_x, particle_y - self.camera_y), particle_size)
            
            for laser in self.lasers:
                if laser['timer'] > laser['fire_frame']:
                    # Warning phase with pulsing
                    pulse = int(abs(math.sin(laser['timer'] * 0.2)) * 100) + 100
                    pygame.draw.rect(self.screen, (*YELLOW, pulse), (laser['rect'].x - self.camera_x, 0, laser['rect'].width, SCREEN_HEIGHT), 3)
                else:
                    # Active laser with glow
                    glow_width = laser['rect'].width + 20
                    glow_surf = pygame.Surface((glow_width, SCREEN_HEIGHT), pygame.SRCALPHA)
                    glow_surf.fill((*RED, 100))
                    self.screen.blit(glow_surf, (laser['rect'].x - self.camera_x - 10, 0))
                    pygame.draw.rect(self.screen, RED, (laser['rect'].x - self.camera_x, 0, laser['rect'].width, SCREEN_HEIGHT))
            
            if hasattr(self, 'miniboss_manager') and self.miniboss_manager.active:
                self.miniboss_manager.draw(self.screen, self.camera_x, self.camera_y)
            
            if self.boss and not (hasattr(self, 'miniboss_manager') and self.miniboss_manager.active):
                self.boss.draw(self.screen, self.camera_x, self.camera_y)
            if self.player:
                self.player.draw(self.screen, self.camera_x, self.camera_y)
            
            for proj in self.projectiles:
                proj.draw(self.screen, self.camera_x, self.camera_y)
            
            for minion in self.minions:
                minion.draw(self.screen, self.camera_x, self.camera_y)
            
            for orb in self.healing_orbs:
                orb.draw(self.screen, self.camera_x, self.camera_y)
            
            # Currency HUD
            currency_text = self.menu.font_small.render(f"Currency: {self.currency}", True, YELLOW)
            self.screen.blit(currency_text, (10, 10))
            
            # Platform hazard warning (Phase 2)
            if self.platform_hazard_active and self.boss and self.boss.phase == 2:
                if not self.platforms_visible:
                    # Animated warning with pulse
                    pulse_alpha = int(abs(math.sin(pygame.time.get_ticks() * 0.01)) * 100) + 155
                    warning_surf = pygame.Surface((SCREEN_WIDTH, 60), pygame.SRCALPHA)
                    warning_surf.fill((*RED, pulse_alpha // 2))
                    self.screen.blit(warning_surf, (0, 80))
                    
                    warning = self.menu.font_medium.render("PLATFORMS DISABLED!", True, RED)
                    self.screen.blit(warning, (SCREEN_WIDTH // 2 - warning.get_width() // 2, 100))
                    timer_text = self.menu.font_small.render(f"{self.platform_disappear_timer // 60 + 1}s", True, RED)
                    self.screen.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 140))
                else:
                    # Show countdown to next disappearance
                    if self.platform_disappear_timer <= 300:  # Last 5 seconds
                        urgency_color = RED if self.platform_disappear_timer <= 120 else ORANGE
                        pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.015)) * 50) + 50
                        warning = self.menu.font_small.render(f"Platforms disappearing in {self.platform_disappear_timer // 60 + 1}s", True, urgency_color)
                        warning_surf = pygame.Surface((warning.get_width() + 20, 40), pygame.SRCALPHA)
                        warning_surf.fill((*urgency_color, pulse))
                        self.screen.blit(warning_surf, (SCREEN_WIDTH // 2 - warning.get_width() // 2 - 10, 90))
                        self.screen.blit(warning, (SCREEN_WIDTH // 2 - warning.get_width() // 2, 100))
            
            # Boss Phase 2 transition overlay
            if self.boss and self.boss.phase2_transition_active:
                # Dark overlay
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = int(abs(math.sin(self.boss.phase2_transition_timer * 0.05)) * 100)
                overlay.fill((*BLACK, alpha))
                self.screen.blit(overlay, (0, 0))
                
                # Phase 2 announcement
                progress = self.boss.phase2_transition_timer / self.boss.phase2_transition_duration
                if progress < 0.5:
                    scale = progress * 4
                    font_size = int(72 * scale)
                    if font_size > 0:
                        phase_font = pygame.font.Font(None, font_size)
                        phase_text = phase_font.render("PHASE 2", True, RED)
                        self.screen.blit(phase_text, (SCREEN_WIDTH // 2 - phase_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
                else:
                    phase_font = pygame.font.Font(None, 72)
                    phase_text = phase_font.render("PHASE 2", True, RED)
                    pulse_alpha = int(abs(math.sin(progress * math.pi * 8)) * 255)
                    phase_surf = pygame.Surface((phase_text.get_width(), phase_text.get_height()), pygame.SRCALPHA)
                    phase_surf.blit(phase_text, (0, 0))
                    phase_surf.set_alpha(pulse_alpha)
                    self.screen.blit(phase_surf, (SCREEN_WIDTH // 2 - phase_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            
            # Debug mode
            if self.debug_mode and self.player and self.boss:
                # Draw player rect
                pygame.draw.rect(self.screen, GREEN, (self.player.x - self.camera_x, self.player.y - self.camera_y, self.player.width, self.player.height), 2)
                # Draw boss rect
                pygame.draw.rect(self.screen, RED, (self.boss.x - self.camera_x, self.boss.y - self.camera_y, self.boss.width, self.boss.height), 2)
                # Draw stats
                stats = [
                    f"Player: {int(self.player.x)}, {int(self.player.y)}",
                    f"Boss: {int(self.boss.x)}, {int(self.boss.y)}",
                    f"Projectiles: {len(self.projectiles)}",
                    f"Minions: {len(self.minions)}",
                    f"Fire zones: {len(self.fire_zones)}",
                    f"Godmode: {self.godmode}",
                    f"Boss inv: {self.boss_invincible}",
                    f"Phase: {self.boss.phase}",
                    f"Platforms: {'Visible' if self.platforms_visible else 'Hidden'}"
                ]
                for i, stat in enumerate(stats):
                    text = self.menu.font_tiny.render(stat, True, WHITE)
                    self.screen.blit(text, (10, 100 + i * 20))
        
        elif self.state == GameState.PAUSED:
            # Draw game in background
            for platform in self.platforms:
                pygame.draw.rect(self.screen, PURPLE, (platform.x - self.camera_x, platform.y - self.camera_y, platform.width, platform.height))
            
            if self.boss:
                self.boss.draw(self.screen, self.camera_x, self.camera_y)
            if self.player:
                self.player.draw(self.screen, self.camera_x, self.camera_y)
            
            self.menu.draw_pause_menu(self.screen)
        
        elif self.state == GameState.GAME_OVER:
            text = self.menu.font_large.render("GAME OVER", True, RED)
            restart = self.menu.font_medium.render("PRESS ENTER TO CONTINUE", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 250))
            self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 400))
        
        elif self.state == GameState.VICTORY:
            text = self.menu.font_large.render("VICTORY!", True, GREEN)
            reward = self.menu.font_medium.render("+1000 Currency", True, YELLOW)
            restart = self.menu.font_medium.render("PRESS ENTER TO CONTINUE", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 200))
            self.screen.blit(reward, (SCREEN_WIDTH // 2 - reward.get_width() // 2, 300))
            self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 400))
        
        # Admin login screen
        if self.admin_login_mode:
            panel_surface = pygame.Surface((600, 300))
            panel_surface.set_alpha(230)
            panel_surface.fill(BLACK)
            self.screen.blit(panel_surface, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 150))
            
            pygame.draw.rect(self.screen, PURPLE, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 150, 600, 300), 3)
            
            title = self.menu.font_large.render("ADMIN LOGIN", True, PURPLE)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 2 - 130))
            
            username_label = self.menu.font_medium.render("Username:", True, WHITE)
            self.screen.blit(username_label, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 50))
            username_box = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 10, 500, 40)
            pygame.draw.rect(self.screen, DARK_PURPLE if self.admin_input_field == "username" else (50, 50, 50), username_box)
            pygame.draw.rect(self.screen, PURPLE if self.admin_input_field == "username" else WHITE, username_box, 2)
            username_text = self.menu.font_medium.render(self.admin_username, True, WHITE)
            self.screen.blit(username_text, (SCREEN_WIDTH // 2 - 240, SCREEN_HEIGHT // 2 - 5))
            
            password_label = self.menu.font_medium.render("Password:", True, WHITE)
            self.screen.blit(password_label, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 50))
            password_box = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 90, 500, 40)
            pygame.draw.rect(self.screen, DARK_PURPLE if self.admin_input_field == "password" else (50, 50, 50), password_box)
            pygame.draw.rect(self.screen, PURPLE if self.admin_input_field == "password" else WHITE, password_box, 2)
            password_masked = "*" * len(self.admin_password)
            password_text = self.menu.font_medium.render(password_masked, True, WHITE)
            self.screen.blit(password_text, (SCREEN_WIDTH // 2 - 240, SCREEN_HEIGHT // 2 + 95))
            
            if self.admin_login_attempts > 0:
                attempts_text = self.menu.font_small.render(f"Failed attempts: {self.admin_login_attempts}/3", True, RED)
                self.screen.blit(attempts_text, (SCREEN_WIDTH // 2 - attempts_text.get_width() // 2, SCREEN_HEIGHT // 2 + 140))
            
            hint = self.menu.font_tiny.render("Press ENTER to submit | ESC to cancel", True, YELLOW)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT // 2 + 160))
        
        # Admin panel
        elif self.admin_panel_active and self.admin_authenticated:
            panel_surface = pygame.Surface((SCREEN_WIDTH, 400))
            panel_surface.set_alpha(200)
            panel_surface.fill(BLACK)
            self.screen.blit(panel_surface, (0, SCREEN_HEIGHT - 400))
            
            title = self.menu.font_medium.render("ADMIN PANEL (F2 to close)", True, YELLOW)
            self.screen.blit(title, (20, SCREEN_HEIGHT - 390))
            
            y = SCREEN_HEIGHT - 350
            for line in self.admin_history[-12:]:
                text = self.menu.font_tiny.render(line, True, GREEN)
                self.screen.blit(text, (20, y))
                y += 25
            
            input_text = f"> {self.admin_input}_"
            input_surface = self.menu.font_tiny.render(input_text, True, WHITE)
            pygame.draw.rect(self.screen, DARK_PURPLE, (10, SCREEN_HEIGHT - 50, SCREEN_WIDTH - 20, 40))
            self.screen.blit(input_surface, (20, SCREEN_HEIGHT - 45))
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(int(FPS * self.menu.game_speed))
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
