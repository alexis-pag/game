import pygame
import random
import math
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

class GameState(Enum):
    START_MENU = 1
    PLAYING = 2
    GAME_OVER = 3
    VICTORY = 4

class Player:
    def __init__(self):
        self.width, self.height = 40, 60
        self.x, self.y = 400, 800
        self.vel_x, self.vel_y = 0, 0
        self.max_hp, self.hp = 200, 200
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
        
        self.parrying = False
        self.fire_slow = False
        self.burn_damage_timer = 0
        
    def update(self, platforms, walls, temp_walls, fire_zones, mouse_pos, camera_x, camera_y):
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
            
            if self.fire_slow:
                speed *= 0.5
            if self.charging:
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
                    elif self.vel_x < 0:
                        self.x = platform.right
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
        damage = 2 + (charge - 25) * 14 / 175
        damage = max(2, min(16, damage))
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
            beam_length = 300
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
    
    def take_damage(self):
        self.hp -= 1
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
        pygame.display.set_caption("Hollow Knight Boss Fight")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.START_MENU
        
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
        
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Admin panel
        self.admin_panel_active = False
        self.admin_input = ""
        self.admin_history = []
        self.admin_scroll = 0
        self.godmode = False
        self.boss_invincible = False
        self.paused = False
        self.camera_follow = True
        self.debug_mode = False
        
        # Admin authentication
        self.admin_authenticated = False
        self.admin_login_mode = False
        self.admin_username = ""
        self.admin_password = ""
        self.admin_input_field = "username"  # "username" or "password"
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
    
    def start_game(self):
        self.state = GameState.PLAYING
        self.player = Player()
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
                self.admin_history.append("TOO MANY FAILED ATTEMPTS - Panel locked for 10 seconds")
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
                self.player = Player()
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
            elif parts[0] == "kill" and parts[1] == "boss" and self.boss:
                self.boss.hp = 0
                self.admin_history.append("Boss killed")
            
            elif parts[0] == "boss_hp" and len(parts) >= 2 and self.boss:
                self.boss.hp = int(parts[1])
                self.admin_history.append(f"Boss HP set to {parts[1]}")
            
            elif parts[0] == "boss" and len(parts) >= 2:
                if parts[1] == "phase1" and self.boss:
                    self.boss.phase = 1
                    self.admin_history.append("Boss forced to Phase 1")
                elif parts[1] == "phase2" and self.boss:
                    self.boss.enter_phase_2()
                    self.admin_history.append("Boss forced to Phase 2")
                elif parts[1] == "reset":
                    self.boss = Boss()
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
                elif parts[1] == "cooldowns" and parts[2] == "reset" and self.boss:
                    self.boss.fireball_cooldown = 0
                    self.boss.laser_cooldown = 0
                    self.boss.shockwave_cooldown = 0
                    self.boss.minion_cooldown = 0
                    self.admin_history.append("Boss cooldowns reset")
                elif parts[1] == "phase" and len(parts) >= 3:
                    phase = int(parts[2])
                    if phase == 1:
                        self.boss.phase = 1
                    elif phase == 2:
                        self.boss.enter_phase_2()
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
                elif parts[1] == "follow":
                    self.camera_follow = parts[2] == "on" if len(parts) > 2 else not self.camera_follow
                    self.admin_history.append(f"Camera follow: {'ON' if self.camera_follow else 'OFF'}")
            
            # Debug mode
            elif parts[0] == "debug":
                self.debug_mode = parts[1] == "on" if len(parts) > 1 else not self.debug_mode
                self.admin_history.append(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
            
            # Help command
            elif parts[0] == "help":
                self.admin_history.append("=== ADMIN COMMANDS ===")
                self.admin_history.append("godmode on/off, set hp/max_hp/speed/jump/dash <val>")
                self.admin_history.append("tp <x> <y>, heal, reset_player, parry on/off")
                self.admin_history.append("kill boss, boss_hp <val>, boss phase1/phase2/reset")
                self.admin_history.append("boss teleport <x> <y>, boss invincible on/off")
                self.admin_history.append("boss fireball/laser/shockwave/summon_minions")
                self.admin_history.append("spawn lava/fireball/orb/minion <x> <y>")
                self.admin_history.append("clear projectiles/minions/fire/orbs")
                self.admin_history.append("win, lose, restart, pause on/off")
                self.admin_history.append("camera <x> <y>, camera follow on/off, debug on/off")
                self.admin_history.append("logout - Log out of admin panel")
            
            elif parts[0] == "logout":
                self.admin_authenticated = False
                self.admin_panel_active = False
                self.admin_history.append("Logged out successfully")
            
            else:
                self.admin_history.append(f"Unknown command: {cmd}")
        
        except Exception as e:
            self.admin_history.append(f"Error: {str(e)}")
        
        # Keep history limited
        if len(self.admin_history) > 20:
            self.admin_history = self.admin_history[-20:]
    
    def boss_ai(self):
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
        if self.paused:
            return
            
        if self.state == GameState.PLAYING and self.player and self.boss:
            mouse_pos = pygame.mouse.get_pos()
            self.player.update(self.platforms, self.walls, self.temp_walls, self.fire_zones, mouse_pos, self.camera_x, self.camera_y)
            
            # Godmode
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
                            for _ in range(int(proj.damage)):
                                self.boss.take_damage()
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
            
            target_x = self.player.x - SCREEN_WIDTH // 2
            target_y = self.player.y - SCREEN_HEIGHT // 2
            if self.camera_follow:
                self.camera_x += (target_x - self.camera_x) * 0.1
                self.camera_y += (target_y - self.camera_y) * 0.1
            self.camera_x = max(0, min(self.camera_x, MAP_WIDTH - SCREEN_WIDTH))
            self.camera_y = max(0, min(self.camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
            
            if self.player.hp <= 0:
                self.state = GameState.GAME_OVER
            elif self.boss.hp <= 0:
                self.state = GameState.VICTORY
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Toggle admin panel with F2
                if event.key == pygame.K_F2:
                    if not self.admin_authenticated and not self.admin_login_mode:
                        # Open login screen
                        self.admin_login_mode = True
                        self.admin_username = ""
                        self.admin_password = ""
                        self.admin_input_field = "username"
                        self.admin_history.append("=== ADMIN LOGIN ===")
                        self.admin_history.append("Enter username...")
                    elif self.admin_authenticated:
                        # Toggle admin panel if already logged in
                        self.admin_panel_active = not self.admin_panel_active
                        if self.admin_panel_active:
                            self.admin_history.append("=== ADMIN PANEL OPENED ===")
                    return
                
                # Admin login input
                if self.admin_login_mode:
                    if event.key == pygame.K_RETURN:
                        if self.admin_input_field == "username":
                            self.admin_input_field = "password"
                            self.admin_history.append("Enter password...")
                        elif self.admin_input_field == "password":
                            self.check_admin_login()
                    elif event.key == pygame.K_BACKSPACE:
                        if self.admin_input_field == "username":
                            self.admin_username = self.admin_username[:-1]
                        else:
                            self.admin_password = self.admin_password[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.admin_login_mode = False
                        self.admin_username = ""
                        self.admin_password = ""
                    elif event.unicode:
                        if self.admin_input_field == "username" and len(self.admin_username) < 20:
                            self.admin_username += event.unicode
                        elif self.admin_input_field == "password" and len(self.admin_password) < 20:
                            self.admin_password += event.unicode
                    return
                
                # Admin panel input (only if authenticated)
                if self.admin_panel_active and self.admin_authenticated:
                    if event.key == pygame.K_RETURN:
                        if self.admin_input.strip():
                            self.execute_admin_command(self.admin_input)
                            self.admin_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.admin_input = self.admin_input[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.admin_panel_active = False
                    elif event.unicode and len(self.admin_input) < 50:
                        self.admin_input += event.unicode
                    return
                
                if self.state == GameState.START_MENU and event.key == pygame.K_RETURN:
                    self.start_game()
                elif self.state in [GameState.GAME_OVER, GameState.VICTORY] and event.key == pygame.K_RETURN:
                    self.start_game()
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_SPACE:
                        self.player.jump()
                    elif event.key == pygame.K_a:
                        self.player.dash()
                    elif event.key == pygame.K_f:
                        self.player.parrying = True
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_f and self.state == GameState.PLAYING:
                    self.player.parrying = False
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == GameState.PLAYING:
                if event.button == 1:
                    if self.player.basic_attack():
                        player_rect = pygame.Rect(self.player.x - 30, self.player.y - 30, self.player.width + 60, self.player.height + 60)
                        boss_rect = pygame.Rect(self.boss.x, self.boss.y, self.boss.width, self.boss.height)
                        if player_rect.colliderect(boss_rect) and not self.boss_invincible:
                            self.boss.take_damage()
                elif event.button == 3:
                    self.player.start_charging()
            if event.type == pygame.MOUSEBUTTONUP and self.state == GameState.PLAYING:
                if event.button == 3:
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
        
        if self.state == GameState.START_MENU:
            title = self.font_large.render("HOLLOW KNIGHT BOSS FIGHT", True, PURPLE)
            start = self.font_medium.render("PRESS ENTER TO START", True, WHITE)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))
            self.screen.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2, 400))
            
            controls = ["Q/D - Move", "SPACE - Jump", "A - Dash", "LEFT CLICK - Basic Attack", "RIGHT CLICK - Charged Attack", "F - Parry", "ESC - Quit"]
            y = 500
            for ctrl in controls:
                text = self.font_small.render(ctrl, True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
                y += 30
        
        elif self.state == GameState.PLAYING:
            for platform in self.platforms:
                pygame.draw.rect(self.screen, PURPLE, (platform.x - self.camera_x, platform.y - self.camera_y, platform.width, platform.height))
            
            for wall in self.temp_walls:
                pygame.draw.rect(self.screen, DARK_PURPLE, (wall['rect'].x - self.camera_x, wall['rect'].y - self.camera_y, wall['rect'].width, wall['rect'].height))
            
            for fire in self.fire_zones:
                pygame.draw.rect(self.screen, RED, (fire['rect'].x - self.camera_x, fire['rect'].y - self.camera_y, fire['rect'].width, fire['rect'].height))
            
            for laser in self.lasers:
                if laser['timer'] > laser['fire_frame']:
                    pygame.draw.rect(self.screen, YELLOW, (laser['rect'].x - self.camera_x, 0, laser['rect'].width, SCREEN_HEIGHT), 3)
                else:
                    pygame.draw.rect(self.screen, RED, (laser['rect'].x - self.camera_x, 0, laser['rect'].width, SCREEN_HEIGHT))
            
            self.boss.draw(self.screen, self.camera_x, self.camera_y)
            self.player.draw(self.screen, self.camera_x, self.camera_y)
            
            for proj in self.projectiles:
                proj.draw(self.screen, self.camera_x, self.camera_y)
            
            for minion in self.minions:
                minion.draw(self.screen, self.camera_x, self.camera_y)
            
            for orb in self.healing_orbs:
                orb.draw(self.screen, self.camera_x, self.camera_y)
            
            # Debug mode
            if self.debug_mode:
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
                    f"Boss inv: {self.boss_invincible}"
                ]
                for i, stat in enumerate(stats):
                    text = self.font_small.render(stat, True, WHITE)
                    self.screen.blit(text, (10, 100 + i * 25))
        
        elif self.state == GameState.GAME_OVER:
            text = self.font_large.render("GAME OVER", True, RED)
            restart = self.font_medium.render("PRESS ENTER TO RESTART", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 250))
            self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 400))
        
        elif self.state == GameState.VICTORY:
            text = self.font_large.render("VICTORY!", True, GREEN)
            restart = self.font_medium.render("PRESS ENTER TO RESTART", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 250))
            self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 400))
        
        # Draw admin panel
        if self.admin_login_mode:
            # Login screen
            panel_surface = pygame.Surface((600, 300))
            panel_surface.set_alpha(230)
            panel_surface.fill(BLACK)
            self.screen.blit(panel_surface, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 150))
            
            # Border
            pygame.draw.rect(self.screen, PURPLE, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 150, 600, 300), 3)
            
            # Title
            title = self.font_large.render("ADMIN LOGIN", True, PURPLE)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 2 - 130))
            
            # Username field
            username_label = self.font_medium.render("Username:", True, WHITE)
            self.screen.blit(username_label, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 50))
            username_box = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 10, 500, 40)
            pygame.draw.rect(self.screen, DARK_PURPLE if self.admin_input_field == "username" else (50, 50, 50), username_box)
            pygame.draw.rect(self.screen, PURPLE if self.admin_input_field == "username" else WHITE, username_box, 2)
            username_text = self.font_medium.render(self.admin_username, True, WHITE)
            self.screen.blit(username_text, (SCREEN_WIDTH // 2 - 240, SCREEN_HEIGHT // 2 - 5))
            
            # Password field
            password_label = self.font_medium.render("Password:", True, WHITE)
            self.screen.blit(password_label, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 50))
            password_box = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 90, 500, 40)
            pygame.draw.rect(self.screen, DARK_PURPLE if self.admin_input_field == "password" else (50, 50, 50), password_box)
            pygame.draw.rect(self.screen, PURPLE if self.admin_input_field == "password" else WHITE, password_box, 2)
            password_masked = "*" * len(self.admin_password)
            password_text = self.font_medium.render(password_masked, True, WHITE)
            self.screen.blit(password_text, (SCREEN_WIDTH // 2 - 240, SCREEN_HEIGHT // 2 + 95))
            
            # Instructions
            if self.admin_login_attempts > 0:
                attempts_text = self.font_small.render(f"Failed attempts: {self.admin_login_attempts}/3", True, RED)
                self.screen.blit(attempts_text, (SCREEN_WIDTH // 2 - attempts_text.get_width() // 2, SCREEN_HEIGHT // 2 + 140))
            
            hint = self.font_small.render("Press ENTER to submit | ESC to cancel", True, YELLOW)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT // 2 + 160))
        
        elif self.admin_panel_active and self.admin_authenticated:
            # Semi-transparent background
            panel_surface = pygame.Surface((SCREEN_WIDTH, 400))
            panel_surface.set_alpha(200)
            panel_surface.fill(BLACK)
            self.screen.blit(panel_surface, (0, SCREEN_HEIGHT - 400))
            
            # Title
            title = self.font_medium.render("ADMIN PANEL (F2 to close)", True, YELLOW)
            self.screen.blit(title, (20, SCREEN_HEIGHT - 390))
            
            # History
            y = SCREEN_HEIGHT - 350
            for line in self.admin_history[-12:]:
                text = self.font_small.render(line, True, GREEN)
                self.screen.blit(text, (20, y))
                y += 25
            
            # Input line
            input_text = f"> {self.admin_input}_"
            input_surface = self.font_small.render(input_text, True, WHITE)
            pygame.draw.rect(self.screen, DARK_PURPLE, (10, SCREEN_HEIGHT - 50, SCREEN_WIDTH - 20, 40))
            self.screen.blit(input_surface, (20, SCREEN_HEIGHT - 45))
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
