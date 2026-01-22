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

class GameState(Enum):
    MAIN_MENU = 0
    START_MENU = 1
    PLAYING = 2
    GAME_OVER = 3
    VICTORY = 4
    PAUSED = 5
    SHOP = 6
    SETTINGS = 7

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
    
    def save_meta_progression(self, currency, items):
        """Save ONLY meta progression data - never runtime state"""
        # Extract only owned items and their equipped status
        owned_items = []
        for item in items:
            if item.owned:
                owned_items.append({
                    'name': item.name,
                    'type': item.type,
                    'level': item.level,
                    'equipped': item.equipped
                })
        
        # Find highest unlocked tiers
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
            # Meta unlocks
            'unlocked_boss_phases': []  # Could add phase unlocks here
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
            
            return meta_data
        except Exception as e:
            print(f"Meta load error: {e}")
            return None
    
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
        
        self.main_options = ["Start Game", "Shop", "Settings", "Exit (F5)"]  # REMOVED "Load Game"
        self.pause_options = ["Return to Menu (Run Lost)", "Quit Game (F5)"]  # CHANGED pause options
        self.settings_options = ["Volume: 50%", "Speed: Normal", "Back"]
        
        self.selected = 0
        self.volume = 50
        self.game_speed = 1.0
        
        self.notification = ""
        self.notification_timer = 0
    
    def navigate(self, direction, current_state):
        if current_state == GameState.MAIN_MENU:
            options = self.main_options
        elif current_state == GameState.PAUSED:
            options = self.pause_options
        elif current_state == GameState.SETTINGS:
            options = self.settings_options
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
        self.burn_damage_timer = 0
    
    def update(self, platforms, walls, temp_walls, fire_zones, mouse_pos, camera_x, camera_y, game_instance=None):
        keys = pygame.key.get_pressed()
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        if self.charging:
            self.charge_percent = min(self.charge_percent + self.charge_rate, self.max_charge)
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
            if self.dash_timer <= 0:
                self.dashing = False
                self.invulnerable = False
        else:
            self.vel_x = 0
            speed = self.speed
            
            # Sniper cannot move while aiming
            if self.weapon_type == "sniper" and self.charging:
                speed = 0
            elif self.fire_slow:
                speed *= 0.5
            elif self.charging:
                speed *= 0.25 if self.charge_percent >= self.max_charge else 0.5
            
            if keys[pygame.K_q]:
                self.vel_x = -speed
            if keys[pygame.K_d]:
                self.vel_x = speed
            
            if self.on_wall and self.vel_y > 0:
                self.vel_y += self.gravity * 0.3
            else:
                self.vel_y += self.gravity
        
        self.x += self.vel_x
        self.check_collision(platforms, walls, temp_walls, 'x')
        self.y += self.vel_y
        
        # Only check collision with platforms if they're visible
        if game_instance is not None and hasattr(game_instance, 'platforms_visible'):
            if game_instance.platforms_visible:
                self.check_collision(platforms, walls, temp_walls, 'y')
            else:
                # No platform collision when invisible - only gravity
                self.on_ground = False
                self.on_wall = False
                # Still check wall collisions
                for wall in walls + [w['rect'] for w in temp_walls]:
                    player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
                    if player_rect.colliderect(wall) and self.vel_y > 0:
                        self.y = wall.top - self.height
                        self.vel_y = 0
                        self.on_ground = True
                        self.jumps_left = 2
        else:
            self.check_collision(platforms, walls, temp_walls, 'y')
        
        self.x = max(0, min(self.x, MAP_WIDTH - self.width))
        self.y = max(0, min(self.y, MAP_HEIGHT - self.height))
        
        self.fire_slow = False
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for fire in fire_zones:
            if player_rect.colliderect(fire['rect']):
                self.fire_slow = True
                if not self.dashing:
                    self.burn_damage_timer += 1
                    if self.burn_damage_timer >= 30:
                        self.hp -= 2
                        self.burn_damage_timer = 0
        
        if not self.fire_slow:
            self.burn_damage_timer = 0
    
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
        x, y = self.x - camera_x, self.y - camera_y
        color = YELLOW if self.dashing else BLUE
        pygame.draw.rect(screen, color, (x, y, self.width, self.height))
        
        if self.charging:
            center_x, center_y = x + self.width // 2, y + self.height // 2
            
            if self.weapon_type == "sniper":
                # Draw circular POV cursor at mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                pygame.draw.circle(screen, RED, (mouse_x, mouse_y), 30, 2)
                pygame.draw.circle(screen, RED, (mouse_x, mouse_y), 5)
                pygame.draw.line(screen, RED, (mouse_x - 35, mouse_y), (mouse_x - 25, mouse_y), 2)
                pygame.draw.line(screen, RED, (mouse_x + 35, mouse_y), (mouse_x + 25, mouse_y), 2)
                pygame.draw.line(screen, RED, (mouse_x, mouse_y - 35), (mouse_x, mouse_y - 25), 2)
                pygame.draw.line(screen, RED, (mouse_x, mouse_y + 35), (mouse_x, mouse_y + 25), 2)
            else:
                # Regular beam
                beam_length = 600 if self.weapon_type == "crossbow" else 300
                end_x = center_x + math.cos(self.aim_angle) * beam_length
                end_y = center_y + math.sin(self.aim_angle) * beam_length
                beam_color = self.get_charge_color()
                thickness = 3 + int(self.charge_percent / 50)
                pygame.draw.line(screen, beam_color, (center_x, center_y), (end_x, end_y), thickness)
                charge_radius = 10 + int(self.charge_percent / 20)
                pygame.draw.circle(screen, beam_color, (int(end_x), int(end_y)), charge_radius, 2)
        
        bar_width, bar_height = 60, 8
        pygame.draw.rect(screen, RED, (x - 10, y - 20, bar_width, bar_height))
        health_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (x - 10, y - 20, health_width, bar_height))
        
        if self.dash_cooldown > 0:
            cooldown_width = int((self.dash_cooldown / self.dash_cooldown_max) * bar_width)
            pygame.draw.rect(screen, ORANGE, (x - 10, y - 30, cooldown_width, 4))

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
    
    def update(self):
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
        
        if self.hp <= self.max_hp // 2 and self.phase == 1:
            self.phase = 2
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
    
    def take_damage(self, damage):
        self.hp -= damage
        self.hits_taken += 1
        self.flash_timer = 5
    
    def draw(self, screen, camera_x, camera_y):
        x, y = self.x - camera_x, self.y - camera_y
        color = WHITE if self.flash_timer > 0 else (RED if self.phase == 2 else PURPLE)
        pygame.draw.rect(screen, color, (x, y, self.width, self.height))
        
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

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Hollow Knight Boss Fight - Enhanced")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MAIN_MENU
        
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
        
        # Meta progression data (persists between runs)
        self.currency = 0  # Loaded from meta save
        self.total_damage_dealt = 0  # Runtime only - NOT saved
        
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
        self.total_damage_dealt = 0
        self.platform_disappear_timer = 0
        self.platforms_visible = True
        self.platform_hazard_active = False
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
        meta_data = self.save_manager.load_meta_progression(self.shop.items)
        if meta_data:
            self.currency = meta_data['total_credits']
            self.menu.show_notification(f"Meta progression loaded! Credits: {self.currency}")
        else:
            # No save exists - start fresh
            self.currency = 0
    
    def save_meta_progression(self):
        """Save ONLY meta progression - never runtime state"""
        if self.save_manager.save_meta_progression(self.currency, self.shop.items):
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
        
        # Get equipped stats from shop
        max_hp, base_damage, weapon_type = self.shop.get_equipped_stats()
        
        self.player = Player(max_hp, base_damage, weapon_type)
        self.boss = Boss()
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
            
        if self.state == GameState.PLAYING and self.player and self.boss:
            mouse_pos = pygame.mouse.get_pos()
            self.player.update(self.platforms, self.walls, self.temp_walls, self.fire_zones, mouse_pos, self.camera_x, self.camera_y, self)
            
            if self.godmode and self.player.hp < self.player.max_hp:
                self.player.hp = self.player.max_hp
            
            self.boss.update()
            self.boss_ai()
            
            for proj in self.projectiles[:]:
                proj.update()
                proj_rect = pygame.Rect(proj.x - proj.radius, proj.y - proj.radius, proj.radius * 2, proj.radius * 2)
                
                if proj.type == 'charged_attack':
                    boss_rect = pygame.Rect(self.boss.x, self.boss.y, self.boss.width, self.boss.height)
                    if proj_rect.colliderect(boss_rect):
                        if not self.boss_invincible:
                            damage = int(proj.damage)
                            self.boss.take_damage(damage)
                            self.total_damage_dealt += damage
                            
                            # Award currency: 2 credits per 10 damage
                            credits_earned = (self.total_damage_dealt // 10) * 2
                            previous_credits = ((self.total_damage_dealt - damage) // 10) * 2
                            new_credits = credits_earned - previous_credits
                            if new_credits > 0:
                                self.currency += new_credits
                        self.projectiles.remove(proj)
                        continue
                    if proj.x < 0 or proj.x > MAP_WIDTH or proj.y < 0 or proj.y > MAP_HEIGHT:
                        self.projectiles.remove(proj)
                        continue
                
                player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
                if proj_rect.colliderect(player_rect) and not self.player.invulnerable and proj.type != 'charged_attack' and not self.godmode:
                    damage = proj.damage // 2 if self.player.parrying else proj.damage
                    self.player.hp -= damage
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
                    damage = 5 // 2 if self.player.parrying else 5
                    self.player.hp -= damage
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
                        damage = 30 // 2 if self.player.parrying else 30
                        self.player.hp -= damage
            
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
                        # Platforms reappear - wait 20 seconds (1200 frames)
                        self.platform_disappear_timer = 1200
                    else:
                        # Platforms disappear - wait 5 seconds (300 frames)
                        self.platform_disappear_timer = 300
            
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
                    if event.key in [pygame.K_UP, pygame.K_DOWN]:
                        direction = -1 if event.key == pygame.K_UP else 1
                        self.menu.navigate(direction, self.state)
                    elif event.key == pygame.K_RETURN:
                        option = self.menu.main_options[self.menu.selected]
                        if option == "Start Game":
                            self.start_game()
                        elif option == "Shop":
                            self.state = GameState.SHOP
                            self.shop.selected_index = 0
                        elif option == "Settings":
                            self.state = GameState.SETTINGS
                            self.menu.selected = 0
                        elif option == "Exit (F5)":
                            self.running = False
                
                # Pause Menu
                elif self.state == GameState.PAUSED:
                    if event.key in [pygame.K_UP, pygame.K_DOWN]:
                        direction = -1 if event.key == pygame.K_UP else 1
                        self.menu.navigate(direction, self.state)
                    elif event.key == pygame.K_RETURN:
                        option = self.menu.pause_options[self.menu.selected]
                        if option == "Return to Menu (Run Lost)":
                            self.return_to_menu_run_lost()
                        elif option == "Quit Game (F5)":
                            self.running = False
                
                # Shop
                elif self.state == GameState.SHOP:
                    if event.key == pygame.K_UP:
                        self.shop.navigate(-1)
                    elif event.key == pygame.K_DOWN:
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
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_f and self.state == GameState.PLAYING and self.player:
                    self.player.parrying = False
            
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == GameState.PLAYING and self.player and self.boss:
                if event.button == 1:  # Left click - Basic attack
                    if self.player.basic_attack():
                        player_rect = pygame.Rect(self.player.x - 30, self.player.y - 30, self.player.width + 60, self.player.height + 60)
                        boss_rect = pygame.Rect(self.boss.x, self.boss.y, self.boss.width, self.boss.height)
                        if player_rect.colliderect(boss_rect) and not self.boss_invincible:
                            damage = self.player.base_damage
                            self.boss.take_damage(damage)
                            self.total_damage_dealt += damage
                            
                            # Award currency: 2 credits per 10 damage
                            credits_earned = (self.total_damage_dealt // 10) * 2
                            previous_credits = ((self.total_damage_dealt - damage) // 10) * 2
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
        
        elif self.state == GameState.PLAYING:
            # Draw game arena
            for platform in self.platforms:
                # Only draw platforms if they're visible (Phase 2 mechanic)
                if self.platforms_visible:
                    pygame.draw.rect(self.screen, PURPLE, (platform.x - self.camera_x, platform.y - self.camera_y, platform.width, platform.height))
                else:
                    # Draw faded platforms when invisible
                    s = pygame.Surface((platform.width, platform.height))
                    s.set_alpha(50)
                    s.fill(PURPLE)
                    self.screen.blit(s, (platform.x - self.camera_x, platform.y - self.camera_y))
            
            for wall in self.temp_walls:
                pygame.draw.rect(self.screen, DARK_PURPLE, (wall['rect'].x - self.camera_x, wall['rect'].y - self.camera_y, wall['rect'].width, wall['rect'].height))
            
            for fire in self.fire_zones:
                pygame.draw.rect(self.screen, RED, (fire['rect'].x - self.camera_x, fire['rect'].y - self.camera_y, fire['rect'].width, fire['rect'].height))
            
            for laser in self.lasers:
                if laser['timer'] > laser['fire_frame']:
                    pygame.draw.rect(self.screen, YELLOW, (laser['rect'].x - self.camera_x, 0, laser['rect'].width, SCREEN_HEIGHT), 3)
                else:
                    pygame.draw.rect(self.screen, RED, (laser['rect'].x - self.camera_x, 0, laser['rect'].width, SCREEN_HEIGHT))
            
            if self.boss:
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
                    warning = self.menu.font_medium.render("PLATFORMS DISABLED!", True, RED)
                    self.screen.blit(warning, (SCREEN_WIDTH // 2 - warning.get_width() // 2, 100))
                    timer_text = self.menu.font_small.render(f"{self.platform_disappear_timer // 60 + 1}s", True, RED)
                    self.screen.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 140))
                else:
                    # Show countdown to next disappearance
                    if self.platform_disappear_timer <= 300:  # Last 5 seconds
                        warning = self.menu.font_small.render(f"Platforms disappearing in {self.platform_disappear_timer // 60 + 1}s", True, ORANGE)
                        self.screen.blit(warning, (SCREEN_WIDTH // 2 - warning.get_width() // 2, 100))
            
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
