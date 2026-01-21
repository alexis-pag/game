import pygame
import random
import math
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
MAP_WIDTH = 2400
MAP_HEIGHT = 1400
FPS = 60

# Colors
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
        self.width = 40
        self.height = 60
        self.x = 400
        self.y = 800
        self.vel_x = 0
        self.vel_y = 0
        self.max_hp = 200
        self.hp = self.max_hp
        self.speed = 6
        self.jump_power = 15
        self.gravity = 0.6
        self.jumps_left = 2
        self.on_ground = False
        self.on_wall = False
        self.wall_side = 0
        
        # Dash
        self.dash_speed = 20
        self.dash_duration = 10
        self.dash_cooldown_max = 30
        self.dash_cooldown = 0
        self.dashing = False
        self.dash_timer = 0
        self.dash_direction = 1
        self.invulnerable = False
        
        # Attack - Basic (Left Click)
        self.attack_cooldown_max = 180
        self.attack_cooldown = 0
        
        # Charged Attack (Right Click)
        self.charging = False
        self.charge_percent = 0
        self.max_charge = 200
        self.charge_rate = 25 / 60  # 25% per second (at 60 FPS)
        self.aim_angle = 0
        
        # Parry
        self.parrying = False
        
        # Status effects
        self.fire_slow = False
        self.burn_damage_timer = 0
        
    def update(self, platforms, walls, temp_walls, fire_zones, mouse_pos, camera_x, camera_y):
        keys = pygame.key.get_pressed()
        
        # Update cooldowns
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Update charged attack
        if self.charging:
            self.charge_percent = min(self.charge_percent + self.charge_rate, self.max_charge)
            
            # Calculate aim angle toward mouse
            world_mouse_x = mouse_pos[0] + camera_x
            world_mouse_y = mouse_pos[1] + camera_y
            dx = world_mouse_x - (self.x + self.width // 2)
            dy = world_mouse_y - (self.y + self.height // 2)
            self.aim_angle = math.atan2(dy, dx)
        
        # Handle dashing
        if self.dashing:
            self.dash_timer -= 1
            self.vel_x = self.dash_speed * self.dash_direction
            self.vel_y = 0
            self.invulnerable = True
            if self.dash_timer <= 0:
                self.dashing = False
                self.invulnerable = False
        else:
            # Normal movement
            self.vel_x = 0
            speed = self.speed
            
            # Apply movement penalties
            if self.fire_slow:
                speed *= 0.5
            if self.charging:
                if self.charge_percent >= self.max_charge:
                    speed *= 0.25  # 75% reduction
                else:
                    speed *= 0.5  # 50% reduction
            
            if keys[pygame.K_q]:
                self.vel_x = -speed
            if keys[pygame.K_d]:
                self.vel_x = speed
            
            # Apply gravity
            if self.on_wall and self.vel_y > 0:
                self.vel_y += self.gravity * 0.3
            else:
                self.vel_y += self.gravity
        
        # Move horizontally
        self.x += self.vel_x
        self.check_collision(platforms, walls, temp_walls, 'x')
        
        # Move vertically
        self.y += self.vel_y
        self.check_collision(platforms, walls, temp_walls, 'y')
        
        # Clamp to map bounds
        self.x = max(0, min(self.x, MAP_WIDTH - self.width))
        self.y = max(0, min(self.y, MAP_HEIGHT - self.height))
        
        # Check fire zones
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
                if player_rect.colliderect(wall):
                    if self.vel_y > 0:
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
                        self.on_wall = True
                        self.wall_side = 1
                        self.jumps_left = 1
                    elif self.vel_x < 0:
                        self.x = wall.right
                        self.on_wall = True
                        self.wall_side = -1
                        self.jumps_left = 1
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
        
        # Calculate damage based on charge (25% = 2 damage, 200% = 16 damage)
        # Linear interpolation: damage = 2 + (charge - 25) * (16 - 2) / (200 - 25)
        damage = 2 + (charge - 25) * 14 / 175
        damage = max(2, min(16, damage))
        
        return {
            'damage': damage,
            'angle': self.aim_angle,
            'charge': charge
        }
    
    def parry(self, active):
        self.parrying = active
    
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
        x = self.x - camera_x
        y = self.y - camera_y
        
        color = YELLOW if self.dashing else BLUE
        pygame.draw.rect(screen, color, (x, y, self.width, self.height))
        
        # Draw charge beam if charging
        if self.charging:
            center_x = x + self.width // 2
            center_y = y + self.height // 2
            beam_length = 300
            end_x = center_x + math.cos(self.aim_angle) * beam_length
            end_y = center_y + math.sin(self.aim_angle) * beam_length
            
            beam_color = self.get_charge_color()
            thickness = 3 + int(self.charge_percent / 50)
            
            pygame.draw.line(screen, beam_color, (center_x, center_y), (end_x, end_y), thickness)
            
            # Draw charge indicator circle
            charge_radius = 10 + int(self.charge_percent / 20)
            pygame.draw.circle(screen, beam_color, (int(end_x), int(end_y)), charge_radius, 2)
        
        # Draw health bar
        bar_width = 60
        bar_height = 8
        pygame.draw.rect(screen, RED, (x - 10, y - 20, bar_width, bar_height))
        health_width = int((self.hp / self.max_hp) * bar_width)
        pygame.draw.rect(screen, GREEN, (x - 10, y - 20, health_width, bar_height))
        
        # Draw dash cooldown bar
        if self.dash_cooldown > 0:
            cooldown_width = int((self.dash_cooldown / self.dash_cooldown_max) * bar_width)
            pygame.draw.rect(screen, ORANGE, (x - 10, y - 30, cooldown_width, 4))
        
        # Draw charge meter
        if self.charging or self.charge_percent > 0:
            charge_bar_width = int((self.charge_percent / self.max_charge) * bar_width)
            pygame.draw.rect(screen, self.get_charge_color(), (x - 10, y - 35, charge_bar_width, 4))

class Boss:
    def __init__(self):
        self.width = 120
        self.height = 140
        self.x = MAP_WIDTH // 2
        self.y = 100  # Always at the top
        self.vel_x = 0
        self.max_hp = 500
        self.hp = self.max_hp
        self.speed = 4
        self.hits_taken = 0
        
        # Movement
        self.move_timer = 0
        self.move_duration = 0
        self.target_x = self.x
        
        # Phase system
        self.phase = 1  # Phase 1 or 2
        
        # Attack cooldowns (in frames) - BASE VALUES
        self.fireball_cooldown_max_base = 120
        self.laser_cooldown_max_base = 240
        self.sword_cooldown_max_base = 600
        self.slam_cooldown_max_base = 360
        self.shockwave_cooldown_max_base = 480
        self.minion_cooldown_max_base = 720
        
        # Current cooldown maxes (adjusted by phase)
        self.fireball_cooldown_max = self.fireball_cooldown_max_base
        self.laser_cooldown_max = self.laser_cooldown_max_base
        self.sword_cooldown_max = self.sword_cooldown_max_base
        self.slam_cooldown_max = self.slam_cooldown_max_base
        self.shockwave_cooldown_max = self.shockwave_cooldown_max_base
        self.minion_cooldown_max = self.minion_cooldown_max_base
        
        # Current cooldowns
        self.fireball_cooldown = 0
        self.laser_cooldown = 0
        self.sword_cooldown = 300
        self.slam_cooldown = 180
        self.shockwave_cooldown = 240
        self.minion_cooldown = 360
        
        self.flash_timer = 0
    
    def update(self):
        if self.fireball_cooldown > 0:
            self.fireball_cooldown -= 1
        if self.laser_cooldown > 0:
            self.laser_cooldown -= 1
        if self.sword_cooldown > 0:
            self.sword_cooldown -= 1
        if self.slam_cooldown > 0:
            self.slam_cooldown -= 1
        if self.shockwave_cooldown > 0:
            self.shockwave_cooldown -= 1
        if self.minion_cooldown > 0:
            self.minion_cooldown -= 1
        if self.flash_timer > 0:
            self.flash_timer -= 1
        
        # Check for phase 2 transition
        if self.hp <= self.max_hp // 2 and self.phase == 1:
            self.enter_phase_2()
        
        # Random horizontal movement
        if self.move_timer <= 0:
            # Choose new random position
            self.target_x = random.randint(200, MAP_WIDTH - 200)
            self.move_duration = random.randint(60, 180)
            self.move_timer = self.move_duration
        
        # Move towards target
        if abs(self.x - self.target_x) > 5:
            if self.x < self.target_x:
                self.x += self.speed
            else:
                self.x -= self.speed
        
        self.move_timer -= 1
        
        # Keep boss at top and within bounds
        self.x = max(100, min(self.x, MAP_WIDTH - 100))
        self.y = 100
    
    def enter_phase_2(self):
        self.phase = 2
        # Divide all cooldowns by 3
        self.fireball_cooldown_max = self.fireball_cooldown_max_base // 3
        self.laser_cooldown_max = self.laser_cooldown_max_base // 3
        self.sword_cooldown_max = self.sword_cooldown_max_base // 3
        self.slam_cooldown_max = self.slam_cooldown_max_base // 3
        self.shockwave_cooldown_max = self.shockwave_cooldown_max_base // 3
        self.minion_cooldown_max = self.minion_cooldown_max_base // 3
    
    def take_damage(self):
        self.hp -= 1
        self.hits_taken += 1
        self.flash_timer = 5
    
    def draw(self, screen, camera_x, camera_y):
        x = self.x - camera_x
        y = self.y - camera_y
        
        # Different color for phase 2
        if self.phase == 2:
            color = WHITE if self.flash_timer > 0 else RED
        else:
            color = WHITE if self.flash_timer > 0 else PURPLE
        pygame.draw.rect(screen, color, (x, y, self.width, self.height))
        
        # Draw health bar at top of screen
        bar_width = 400
        bar_height = 20
        bar_x = SCREEN_WIDTH // 2 - bar_width // 2
        pygame.draw.rect(screen, RED, (bar_x, 20, bar_width, bar_height))
        health_width = int((self.hp / self.max_hp) * bar_width)
        
        # Phase 2 health bar is red, phase 1 is green
        bar_color = ORANGE if self.phase == 2 else GREEN
        pygame.draw.rect(screen, bar_color, (bar_x, 20, health_width, bar_height))
        
        # Phase indicator
        phase_font = pygame.font.Font(None, 36)
        if self.phase == 2:
            phase_text = phase_font.render("PHASE 2", True, RED)
            screen.blit(phase_text, (bar_x + bar_width + 20, 15))

class Projectile:
    def __init__(self, x, y, vel_x, vel_y, damage, proj_type):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.damage = damage
        self.type = proj_type
        self.radius = 15 if proj_type == 'fireball' else 10
        self.active = True
    
    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        if self.type == 'fireball':
            self.vel_y += 0.4
    
    def draw(self, screen, camera_x, camera_y):
        x = int(self.x - camera_x)
        y = int(self.y - camera_y)
        
        if self.type == 'charged_attack':
            # Player's charged attack - different visual
            pygame.draw.circle(screen, WHITE, (x, y), self.radius)
            pygame.draw.circle(screen, BLUE, (x, y), self.radius - 3)
        else:
            color = ORANGE if self.type == 'fireball' else RED
            pygame.draw.circle(screen, color, (x, y), self.radius)

class Minion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.speed = 4
        self.hp = 3
        self.vel_y = 0
        self.gravity = 0.6
    
    def update(self, player, platforms):
        if player.x < self.x:
            self.x -= self.speed
        else:
            self.x += self.speed
        
        self.vel_y += self.gravity
        self.y += self.vel_y
        
        minion_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for platform in platforms:
            if minion_rect.colliderect(platform):
                if self.vel_y > 0:
                    self.y = platform.top - self.height
                    self.vel_y = 0
    
    def draw(self, screen, camera_x, camera_y):
        x = self.x - camera_x
        y = self.y - camera_y
        pygame.draw.rect(screen, DARK_PURPLE, (x, y, self.width, self.height))

class HealingOrb:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.heal_amount = 30
        self.pulse_timer = 0
        self.active = True
    
    def update(self):
        self.pulse_timer += 1
    
    def draw(self, screen, camera_x, camera_y):
        x = int(self.x - camera_x)
        y = int(self.y - camera_y)
        
        # Pulsing effect
        pulse = abs(math.sin(self.pulse_timer * 0.1)) * 3
        current_radius = self.radius + int(pulse)
        
        # Outer glow
        pygame.draw.circle(screen, (0, 255, 100), (x, y), current_radius + 3)
        # Inner orb
        pygame.draw.circle(screen, GREEN, (x, y), current_radius)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Boss Fight")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.START_MENU
        self.frame_count = 0
        
        self.player = None
        self.boss = None
        self.projectiles = []
        self.minions = []
        self.fire_zones = []
        self.lasers = []
        self.temp_walls = []
        self.healing_orbs = []
        self.orb_spawn_timer = 0
        self.laser_spawn_queue = []  # For delayed laser spawning in phase 2
        
        self.platforms = []
        self.walls = []
        self.setup_arena()
        
        self.camera_x = 0
        self.camera_y = 0
        
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
    
    def setup_arena(self):
        # Ground
        self.platforms.append(pygame.Rect(0, MAP_HEIGHT - 50, MAP_WIDTH, 50))
        
        # Bottom platforms
        self.platforms.append(pygame.Rect(300, MAP_HEIGHT - 200, 300, 20))
        self.platforms.append(pygame.Rect(800, MAP_HEIGHT - 200, 300, 20))
        self.platforms.append(pygame.Rect(1400, MAP_HEIGHT - 200, 300, 20))
        self.platforms.append(pygame.Rect(1900, MAP_HEIGHT - 200, 300, 20))
        
        # Mid platforms
        self.platforms.append(pygame.Rect(150, MAP_HEIGHT - 400, 250, 20))
        self.platforms.append(pygame.Rect(600, MAP_HEIGHT - 400, 250, 20))
        self.platforms.append(pygame.Rect(1050, MAP_HEIGHT - 400, 250, 20))
        self.platforms.append(pygame.Rect(1500, MAP_HEIGHT - 400, 250, 20))
        self.platforms.append(pygame.Rect(1950, MAP_HEIGHT - 400, 250, 20))
        
        # Upper platforms
        self.platforms.append(pygame.Rect(400, MAP_HEIGHT - 600, 200, 20))
        self.platforms.append(pygame.Rect(900, MAP_HEIGHT - 600, 200, 20))
        self.platforms.append(pygame.Rect(1400, MAP_HEIGHT - 600, 200, 20))
        self.platforms.append(pygame.Rect(1900, MAP_HEIGHT - 600, 200, 20))
        
        # High platforms
        self.platforms.append(pygame.Rect(200, MAP_HEIGHT - 800, 200, 20))
        self.platforms.append(pygame.Rect(700, MAP_HEIGHT - 800, 200, 20))
        self.platforms.append(pygame.Rect(1200, MAP_HEIGHT - 800, 200, 20))
        self.platforms.append(pygame.Rect(1700, MAP_HEIGHT - 800, 200, 20))
        
        # Very high platforms
        self.platforms.append(pygame.Rect(500, MAP_HEIGHT - 1000, 200, 20))
        self.platforms.append(pygame.Rect(1000, MAP_HEIGHT - 1000, 200, 20))
        self.platforms.append(pygame.Rect(1500, MAP_HEIGHT - 1000, 200, 20))
    
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
        self.frame_count = 0
    
    def update(self):
        self.frame_count += 1
        
        if self.state == GameState.PLAYING:
            self.player.update(self.platforms, self.walls, self.temp_walls, self.fire_zones, pygame.mouse.get_pos(), self.camera_x, self.camera_y)
            
            # Update camera to follow player
            self.camera_x = self.player.x - SCREEN_WIDTH // 2
            self.camera_y = self.player.y - SCREEN_HEIGHT // 2
            self.camera_x = max(0, min(self.camera_x, MAP_WIDTH - SCREEN_WIDTH))
            self.camera_y = max(0, min(self.camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
            
            self.boss.update()
            self.boss_ai()
            
            for proj in self.projectiles[:]:
                proj.update()
                proj_rect = pygame.Rect(proj.x - proj.radius, proj.y - proj.radius, 
                                       proj.radius * 2, proj.radius * 2)
                
                # Check collision with boss for player charged attacks
                if proj.type == 'charged_attack':
                    boss_rect = pygame.Rect(self.boss.x, self.boss.y, 
                                           self.boss.width, self.boss.height)
                    if proj_rect.colliderect(boss_rect):
                        # Damage boss based on charge
                        damage_amount = int(proj.damage)
                        for _ in range(damage_amount):
                            self.boss.take_damage()
                        self.projectiles.remove(proj)
                        continue
                    
                    # Remove if off screen
                    if (proj.x < 0 or proj.x > MAP_WIDTH or 
                        proj.y < 0 or proj.y > MAP_HEIGHT):
                        self.projectiles.remove(proj)
                        continue
                    
                    # Boss projectile collision with player
                    player_rect = pygame.Rect(self.player.x, self.player.y, 
                                             self.player.width, self.player.height)
                    if proj_rect.colliderect(player_rect) and not self.player.invulnerable:
                        if proj.type != 'charged_attack':  # Only boss projectiles damage player
                            damage = proj.damage
                            if self.player.parrying:
                                damage //= 2
                            self.player.hp -= damage
                            self.projectiles.remove(proj)
                            
                            if proj.type == 'fireball':
                                self.fire_zones.append({
                                    'rect': pygame.Rect(proj.x - 40, proj.y - 20, 80, 40),
                                    'timer': 900
                                })
                    
                    elif proj.y > MAP_HEIGHT or proj.x < 0 or proj.x > MAP_WIDTH:
                        if proj.type == 'fireball':
                            # Check if fireball hits any platform
                            landed = False
                            fireball_rect = pygame.Rect(proj.x - 40, proj.y - 20, 80, 40)
                            for platform in self.platforms:
                                if fireball_rect.colliderect(platform):
                                    # Create fire zone on the platform
                                    self.fire_zones.append({
                                        'rect': pygame.Rect(proj.x - 40, platform.top - 40, 80, 40),
                                        'timer': 900
                                    })
                                    landed = True
                                    break
                            
                            # If didn't hit platform and off screen, still create fire on ground
                            if not landed and proj.y > MAP_HEIGHT - 100:
                                self.fire_zones.append({
                                    'rect': pygame.Rect(proj.x - 40, MAP_HEIGHT - 90, 80, 40),
                                    'timer': 900
                                })
                        if proj.type != 'charged_attack':  # Don't remove charged attacks here
                            self.projectiles.remove(proj)
            
            for minion in self.minions[:]:
                minion.update(self.player, self.platforms)
                minion_rect = pygame.Rect(minion.x, minion.y, minion.width, minion.height)
                player_rect = pygame.Rect(self.player.x, self.player.y, 
                                         self.player.width, self.player.height)
                
                if minion_rect.colliderect(player_rect) and not self.player.invulnerable:
                    damage = 5
                    if self.player.parrying:
                        damage //= 2
                    self.player.hp -= damage
                    self.minions.remove(minion)
                
                if minion.hp <= 0:
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
                    player_rect = pygame.Rect(self.player.x, self.player.y, 
                                             self.player.width, self.player.height)
                    if laser['rect'].colliderect(player_rect) and not self.player.invulnerable:
                        damage = 30
                        if self.player.parrying:
                            damage //= 2
                        self.player.hp -= damage
            
            for wall in self.temp_walls[:]:
                wall['timer'] -= 1
                if wall['timer'] <= 0:
                    self.temp_walls.remove(wall)
                
                if random.randint(1, 300) == 1:
                    x = random.randint(400, MAP_WIDTH - 400)
                    y = random.randint(400, MAP_HEIGHT - 400)
                    self.temp_walls.append({
                        'rect': pygame.Rect(x, y, 20, 400),
                        'timer': 480
                    })
                
                # Spawn healing orbs with limits
                self.orb_spawn_timer += 1
                
                # Max 3 orbs at once, respawn every 10 seconds (600 frames)
                if len(self.healing_orbs) < 3 and self.orb_spawn_timer >= 600:
                    x = random.randint(200, MAP_WIDTH - 200)
                    y = random.randint(300, MAP_HEIGHT - 300)
                    self.healing_orbs.append(HealingOrb(x, y))
                    self.orb_spawn_timer = 0
                
                # Update healing orbs
                for orb in self.healing_orbs[:]:
                    orb.update()
                    orb_rect = pygame.Rect(orb.x - orb.radius, orb.y - orb.radius,
                                          orb.radius * 2, orb.radius * 2)
                    player_rect = pygame.Rect(self.player.x, self.player.y,
                                             self.player.width, self.player.height)
                    
                    if orb_rect.colliderect(player_rect):
                        # Heal player but don't exceed max HP, and only if HP > 0
                        if self.player.hp > 0:
                            self.player.hp = min(self.player.hp + orb.heal_amount, self.player.max_hp)
                            self.healing_orbs.remove(orb)
                            # Reset timer to start 10 second countdown for next orb
                            self.orb_spawn_timer = 0
                
                # Process delayed laser spawns (for phase 2)
                for laser_data in self.laser_spawn_queue[:]:
                    laser_data['delay'] -= 1
                    if laser_data['delay'] <= 0:
                        self.lasers.append(laser_data['laser'])
                        self.laser_spawn_queue.remove(laser_data)
                
                target_x = self.player.x - SCREEN_WIDTH // 2
                target_y = self.player.y - SCREEN_HEIGHT // 2
                self.camera_x += (target_x - self.camera_x) * 0.1
                self.camera_y += (target_y - self.camera_y) * 0.1
                
                self.camera_x = max(0, min(self.camera_x, MAP_WIDTH - SCREEN_WIDTH))
                self.camera_y = max(0, min(self.camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
                
                if self.boss.hp <= 0:
                    self.state = GameState.VICTORY
                elif self.player.hp <= 0:
                    self.state = GameState.GAME_OVER
    
    def boss_ai(self):
        if not self.boss:
            return
            
        # Determine multiplier based on phase
        attack_multiplier = 3 if self.boss.phase == 2 else 1
        
        # Fireball attack
        if self.boss.fireball_cooldown == 0:
            for _ in range(attack_multiplier):
                for i in range(5):
                    x = self.boss.x + self.boss.width // 2
                    y = self.boss.y + self.boss.height
                    vel_x = random.uniform(-4, 4)
                    vel_y = random.uniform(-3, 1)
                    self.projectiles.append(Projectile(x, y, vel_x, vel_y, 10, 'fireball'))
            self.boss.fireball_cooldown = self.boss.fireball_cooldown_max
        
        # Laser attack - reduced telegraph time, tripled in phase 2
        if self.boss.laser_cooldown == 0:
            # Base telegraph time reduced by 3 (from 90 to 30, fire at frame 10 instead of 30)
            base_timer = 30
            fire_frame = 10
            
            if self.boss.phase == 1:
                laser_x = self.player.x + self.player.width // 2 - 25
                self.lasers.append({
                    'rect': pygame.Rect(laser_x, 0, 50, MAP_HEIGHT),
                    'timer': base_timer,
                    'fire_frame': fire_frame
                })
            else:
                # Phase 2: spawn 3 lasers with 0.1 second (6 frames) delay
                for i in range(3):
                    offset = random.randint(-100, 100)
                    laser_x = self.player.x + self.player.width // 2 - 25 + offset
                    laser = {
                        'rect': pygame.Rect(laser_x, 0, 50, MAP_HEIGHT),
                        'timer': base_timer,
                        'fire_frame': fire_frame
                    }
                    if i == 0:
                        self.lasers.append(laser)
                    else:
                        # Queue with delay
                        self.laser_spawn_queue.append({
                            'laser': laser,
                            'delay': i * 6  # 6 frames = 0.1 seconds
                        })
            
            self.boss.laser_cooldown = self.boss.laser_cooldown_max
        
        distance = math.sqrt((self.boss.x - self.player.x)**2 + (self.boss.y - self.player.y)**2)
        
        # Shockwave attack
        if self.boss.shockwave_cooldown == 0:
            for _ in range(attack_multiplier):
                direction = 1 if self.player.x > self.boss.x else -1
                self.projectiles.append(Projectile(
                    self.boss.x + self.boss.width // 2,
                    self.boss.y + self.boss.height,
                    direction * 8, 2, 20, 'shockwave'
                ))
            self.boss.shockwave_cooldown = self.boss.shockwave_cooldown_max
        
        # Summon minions
        if self.boss.minion_cooldown == 0:
            for _ in range(attack_multiplier):
                for i in range(3):
                    spawn_x = self.boss.x + random.randint(-100, 100)
                    self.minions.append(Minion(spawn_x, self.boss.y + 200))
            self.boss.minion_cooldown = self.boss.minion_cooldown_max
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                if self.state == GameState.START_MENU:
                    if event.key == pygame.K_RETURN:
                        self.start_game()
                
                elif self.state in [GameState.GAME_OVER, GameState.VICTORY]:
                    if event.key == pygame.K_RETURN:
                        self.start_game()
                
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_SPACE:
                        self.player.jump()
                    elif event.key == pygame.K_a:
                        self.player.dash()
                    elif event.key == pygame.K_f:
                        self.player.parry(True)
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_f:
                    self.player.parry(False)
            
            # Mouse events for attacking
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == GameState.PLAYING:
                    if event.button == 1:  # Left click - basic attack
                        if self.player.basic_attack():
                            # Check if boss is hit (melee range)
                            player_rect = pygame.Rect(self.player.x - 30, self.player.y - 30,
                                                     self.player.width + 60, self.player.height + 60)
                            boss_rect = pygame.Rect(self.boss.x, self.boss.y, 
                                                   self.boss.width, self.boss.height)
                            if player_rect.colliderect(boss_rect):
                                self.boss.take_damage()
                    
                    elif event.button == 3:  # Right click - start charging
                        self.player.start_charging()
            
            if event.type == pygame.MOUSEBUTTONUP:
                if self.state == GameState.PLAYING:
                    if event.button == 3:  # Right click release - fire charged attack
                        attack_data = self.player.release_charged_attack()
                        if attack_data and attack_data['charge'] >= 25:
                            # Spawn charged projectile
                            speed = 15
                            vel_x = math.cos(attack_data['angle']) * speed
                            vel_y = math.sin(attack_data['angle']) * speed
                            
                            start_x = self.player.x + self.player.width // 2
                            start_y = self.player.y + self.player.height // 2
                            
                            self.projectiles.append(Projectile(
                                start_x, start_y, vel_x, vel_y,
                                attack_data['damage'], 'charged_attack'
                            ))
    
    def draw(self):
        self.screen.fill(BLACK)
        
        if self.state == GameState.START_MENU:
            title = self.font_large.render("BOSS FIGHT", True, PURPLE)
            start = self.font_medium.render("PRESS ENTER TO START", True, WHITE)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))
            self.screen.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2, 400))
            
            controls = [
                "Q/D - Move",
                "SPACE - Jump (double jump)",
                "A - Dash",
                "LEFT CLICK - Basic Attack (melee)",
                "RIGHT CLICK (Hold) - Charged Attack (ranged)",
                "F - Parry",
                "ESC - Quit"
            ]
            y = 500
            for ctrl in controls:
                text = self.font_small.render(ctrl, True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
                y += 30
        
        elif self.state == GameState.PLAYING:
            for platform in self.platforms:
                x = platform.x - self.camera_x
                y = platform.y - self.camera_y
                pygame.draw.rect(self.screen, PURPLE, (x, y, platform.width, platform.height))
            
            for wall in self.temp_walls:
                x = wall['rect'].x - self.camera_x
                y = wall['rect'].y - self.camera_y
                pygame.draw.rect(self.screen, DARK_PURPLE, 
                               (x, y, wall['rect'].width, wall['rect'].height))
            
            for fire in self.fire_zones:
                x = fire['rect'].x - self.camera_x
                y = fire['rect'].y - self.camera_y
                pygame.draw.rect(self.screen, RED, 
                               (x, y, fire['rect'].width, fire['rect'].height))
            
            for laser in self.lasers:
                if laser['timer'] > laser['fire_frame']:
                    x = laser['rect'].x - self.camera_x
                    pygame.draw.rect(self.screen, YELLOW, 
                                   (x, 0, laser['rect'].width, SCREEN_HEIGHT), 3)
                else:
                    x = laser['rect'].x - self.camera_x
                    pygame.draw.rect(self.screen, RED, 
                                   (x, 0, laser['rect'].width, SCREEN_HEIGHT))
            
            self.boss.draw(self.screen, self.camera_x, self.camera_y)
            self.player.draw(self.screen, self.camera_x, self.camera_y)
            
            for proj in self.projectiles:
                proj.draw(self.screen, self.camera_x, self.camera_y)
            
            for minion in self.minions:
                minion.draw(self.screen, self.camera_x, self.camera_y)
            
            for orb in self.healing_orbs:
                orb.draw(self.screen, self.camera_x, self.camera_y)
        
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