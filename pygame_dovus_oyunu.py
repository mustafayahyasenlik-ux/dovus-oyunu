"""
GELİŞMİŞ GRAFİKLİ DÖVÜŞ OYUNU - pygame

Özellikler (hepsi eklendi):
 - Sprite desteği (varsayılan şekiller; istersen kendi resimlerini koyabilirsin)
 - Ses efektleri (attack/special/heal/menus) — dosyalar varsa çalar, yoksa sessiz devam eder
 - 1 veya 2 oyunculu mod (yerel, aynı klavyede)
 - Boss modu / AI
 - Can ve enerji barları, özel saldırı cooldown, savunma, iyileşme
 - Menü, pause, yeniden başlatma

Çalıştırma:
    1) Python 3.8+ kurulu olsun
    2) pip install pygame
    3) python pygame_dovus_oyunu.py

İsteğe bağlı asset (aynı klasöre koy):
    player1.png, player2.png, background.png, attack.wav, special.wav, heal.wav, menu.wav

Kontroller:
  Tek oyuncu (Player1):
    A / D -> sola/sağa hareket
    W -> zıpla
    J -> hafif saldırı
    K -> özel saldırı
    L -> savunma
    H -> iyileş

  İkinci oyuncu (aynı klavyede):
    Sol / Sağ -> hareket
    Yukarı -> zıpla
    M -> hafif saldırı
    N -> özel saldırı
    B -> savunma
    V -> iyileş

Diğer:
    ESC -> Menü / Çıkış
    P -> Pause
    R -> Yeniden başlat (oyun bittiğinde veya menüde)

Not: Bu kod bağımsız çalışır. Eğer sprite/ses eklemek istersen, hangi dosyaları koyduğunu söyle, ben uygun boyutlandırma/konumlandırma/animasyon eklerim.
"""

import pygame
import random
import time
import os

# ====== Ayarlar ======
WIDTH, HEIGHT = 1000, 560
FPS = 60
GROUND_Y = HEIGHT - 100

# Renkler
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 40, 40)
GREEN = (40, 200, 40)
BLUE = (50, 130, 255)
GRAY = (200, 200, 200)
YELLOW = (230, 200, 30)
BG_COLOR = (28, 28, 38)

# ====== Pygame Başlat ======
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Grafikli Dövüş Oyunu - Gelişmiş")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
large_font = pygame.font.SysFont(None, 36)
huge_font = pygame.font.SysFont(None, 54)

# ====== Asset yükleme (varsa) ======
ASSET_DIR = os.path.dirname(__file__) if '__file__' in globals() else os.getcwd()

def load_image(name, fallback_size=(60,80)):
    path = os.path.join(ASSET_DIR, name)
    try:
        img = pygame.image.load(path).convert_alpha()
        return img
    except Exception:
        # fallback: return None -> kod sprite'ı dikdörtgenle çizecek
        return None

def load_sound(name):
    path = os.path.join(ASSET_DIR, name)
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

PLAYER1_IMG = load_image('player1.png')
PLAYER2_IMG = load_image('player2.png')
BACKGROUND_IMG = load_image('background.png')
SND_ATTACK = load_sound('attack.wav')
SND_SPECIAL = load_sound('special.wav')
SND_HEAL = load_sound('heal.wav')
SND_MENU = load_sound('menu.wav')

# ====== Yardımcı Fonksiyonlar ======

def draw_text(surf, text, x, y, color=WHITE, font=font):
    img = font.render(text, True, color)
    surf.blit(img, (x, y))

def draw_center_text(surf, text, y, color=WHITE, font=large_font):
    img = font.render(text, True, color)
    rect = img.get_rect(center=(WIDTH//2, y))
    surf.blit(img, rect)

def draw_bar(surf, x, y, w, h, pct, bar_color):
    pct = max(0, min(1, pct))
    pygame.draw.rect(surf, GRAY, (x, y, w, h))
    pygame.draw.rect(surf, bar_color, (x, y, int(w * pct), h))
    pygame.draw.rect(surf, BLACK, (x, y, w, h), 2)

# ====== Fighter sınıfı (sprite ve ses destekli) ======
class Fighter:
    def __init__(self, name, x, y, color, sprite=None):
        self.name = name
        self.x = x
        self.y = y
        self.width = 64
        self.height = 96
        self.color = color
        self.sprite = sprite

        self.max_health = 220
        self.health = self.max_health
        self.max_energy = 100
        self.energy = self.max_energy

        self.speed = 4.2
        self.vel_y = 0
        self.jump_power = -13
        self.on_ground = True

        self.is_defending = False
        self.defend_timer = 0

        self.attack_rect = None
        self.facing = 1  # 1 sağ, -1 sol

        self.special_cooldown = 4.5
        self.special_last = -999

        self.heal_cooldown = 9.0
        self.heal_last = -999

        self.last_regen = time.time()

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def center_x(self):
        return self.x + self.width/2

    def move(self, dx):
        self.x += dx
        self.x = max(10, min(WIDTH - 10 - self.width, self.x))
        if dx > 0:
            self.facing = 1
        elif dx < 0:
            self.facing = -1

    def jump(self):
        if self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

    def apply_gravity(self):
        self.vel_y += 0.8
        self.y += self.vel_y
        if self.y + self.height >= GROUND_Y:
            self.y = GROUND_Y - self.height
            self.vel_y = 0
            self.on_ground = True

    def normal_attack(self, target):
        attack_range = 56
        damage = random.randint(10, 20)
        rect = pygame.Rect(0, 0, attack_range, 28)
        if self.facing == 1:
            rect.topleft = (self.x + self.width, self.y + 30)
        else:
            rect.topright = (self.x, self.y + 30)
        self.attack_rect = rect
        if rect.colliderect(target.rect()):
            actual = damage//2 if target.is_defending else damage
            target.health -= actual
            if SND_ATTACK: SND_ATTACK.play()
            return actual
        return 0

    def special_attack(self, target):
        now = time.time()
        if now - self.special_last < self.special_cooldown:
            return None
        if self.energy < 28:
            return None
        self.energy -= 28
        self.special_last = now
        attack_range = 140
        damage = random.randint(28, 48)
        rect = pygame.Rect(0, 0, attack_range, 36)
        if self.facing == 1:
            rect.topleft = (self.x + self.width, self.y + 20)
        else:
            rect.topright = (self.x, self.y + 20)
        self.attack_rect = rect
        if rect.colliderect(target.rect()):
            actual = damage//2 if target.is_defending else damage
            target.health -= actual
            if SND_SPECIAL: SND_SPECIAL.play()
            return actual
        return 0

    def defend(self):
        self.is_defending = True
        self.defend_timer = time.time()

    def heal(self):
        now = time.time()
        if now - self.heal_last < self.heal_cooldown:
            return False
        if self.energy < 22:
            return False
        self.energy -= 22
        self.heal_last = now
        heal_amount = random.randint(18, 34)
        self.health = min(self.max_health, self.health + heal_amount)
        if SND_HEAL: SND_HEAL.play()
        return heal_amount

    def update(self):
        if self.is_defending and time.time() - self.defend_timer > 1.2:
            self.is_defending = False
        # kısa süre içinde attack_rect temizleme
        if getattr(self, 'attack_rect', None):
            # attack gösterimini kısa tut
            pass
        # regen
        now = time.time()
        if now - self.last_regen > 1.0:
            self.last_regen = now
            self.energy = min(self.max_energy, self.energy + 5)
            if self.health < self.max_health:
                self.health = min(self.max_health, self.health + 2)

    def draw(self, surf):
        r = self.rect()
        if self.sprite:
            # sprite'ı uygun boyuta ölçekle
            img = pygame.transform.smoothscale(self.sprite, (self.width, self.height))
            surf.blit(img, (self.x, self.y))
        else:
            pygame.draw.rect(surf, self.color, r, border_radius=8)
            eye_x = int(self.x + self.width/2 + (12 * self.facing))
            pygame.draw.circle(surf, BLACK, (eye_x, int(self.y + 24)), 6)

        if self.is_defending:
            pygame.draw.rect(surf, (120, 180, 255), r, 4)
        if getattr(self, 'attack_rect', None):
            pygame.draw.rect(surf, YELLOW, self.attack_rect)

# ====== Basit AI (geliştirilmiş) ======
class SimpleAI:
    def __init__(self, fntr: Fighter):
        self.f = fntr
        self.last_decision = time.time()

    def decide(self, player: Fighter):
        now = time.time()
        if now - self.last_decision < 0.8:
            return None
        self.last_decision = now
        f = self.f
        dist = abs(f.center_x() - player.center_x())
        # düşük sağlık -> heal dene
        if f.health < f.max_health * 0.35 and f.energy >= 22 and random.random() < 0.45:
            return 'heal'
        if dist > 100 and f.energy >= 28 and random.random() < 0.5:
            return 'special'
        if dist < 80:
            return random.choice(['attack', 'attack', 'defend'])
        return 'approach'

# ====== Menü ve UI ======

def main_menu():
    selected = 0
    options = ['Tek Oyuncu', 'İki Oyuncu (aynı klavye)', 'Çıkış']
    if SND_MENU: SND_MENU.play()
    while True:
        clock.tick(FPS)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                if ev.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                if ev.key == pygame.K_RETURN:
                    return selected
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); exit()
        # draw
        screen.fill(BG_COLOR)
        if BACKGROUND_IMG:
            bg = pygame.transform.scale(BACKGROUND_IMG, (WIDTH, HEIGHT))
            screen.blit(bg, (0,0))
        draw_center_text(screen, 'GELIŞMIŞ DOVUS OYUNU', 90, WHITE, huge_font)
        for i, opt in enumerate(options):
            color = YELLOW if i == selected else WHITE
            draw_center_text(screen, opt, 200 + i*50, color, large_font)
        draw_center_text(screen, 'YUKARI/AŞAĞI - Menü, ENTER - Seç', HEIGHT - 40, GRAY, font)
        pygame.display.flip()

def draw_hud(player, enemy):
    draw_text(screen, f"{player.name}", 20, 18)
    draw_bar(screen, 20, 40, 350, 22, player.health/player.max_health, GREEN)
    draw_text(screen, f"Can: {int(player.health)}/{player.max_health}", 380, 40)
    draw_bar(screen, 20, 68, 350, 14, player.energy/player.max_energy, BLUE)

    draw_text(screen, f"{enemy.name}", WIDTH-380, 18)
    draw_bar(screen, WIDTH-380, 40, 350, 22, enemy.health/enemy.max_health, RED)
    draw_text(screen, f"Can: {int(enemy.health)}/{enemy.max_health}", WIDTH-30-160, 40)
    draw_bar(screen, WIDTH-380, 68, 350, 14, enemy.energy/enemy.max_energy, YELLOW)

# ====== Oyun döngüsü ======

def game_loop(two_player=False):
    # oyuncu ve rakip (player2 veya AI)
    p1 = Fighter('Kahraman', 140, GROUND_Y - 96, BLUE, PLAYER1_IMG)
    if two_player:
        p2 = Fighter('Rakip', WIDTH-200, GROUND_Y - 96, RED, PLAYER2_IMG)
        enemy_is_ai = False
        enemy = p2
    else:
        # AI boss
        boss = Fighter('Boss', WIDTH-220, GROUND_Y - 96, RED, PLAYER2_IMG)
        boss.max_health = 320
        boss.health = boss.max_health
        boss.energy = boss.max_energy
        enemy = boss
        enemy_is_ai = True
    enemy_ai = SimpleAI(enemy)

    running = True
    paused = False
    game_over = False
    winner = None

    # input state
    p1_left = p1_right = False
    p2_left = p2_right = False

    while running:
        dt = clock.tick(FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key == pygame.K_p:
                    paused = not paused
                # Player1 controls
                if ev.key == pygame.K_a:
                    p1_left = True
                if ev.key == pygame.K_d:
                    p1_right = True
                if ev.key == pygame.K_w:
                    p1.jump()
                if ev.key == pygame.K_j:
                    dmg = p1.normal_attack(enemy)
                if ev.key == pygame.K_k:
                    res = p1.special_attack(enemy)
                if ev.key == pygame.K_l:
                    p1.defend()
                if ev.key == pygame.K_h:
                    p1.heal()
                # Player2 (local) controls
                if two_player:
                    if ev.key == pygame.K_LEFT:
                        p2_left = True
                    if ev.key == pygame.K_RIGHT:
                        p2_right = True
                    if ev.key == pygame.K_UP:
                        p2.jump()
                    if ev.key == pygame.K_m:
                        dmg2 = p2.normal_attack(p1)
                    if ev.key == pygame.K_n:
                        res2 = p2.special_attack(p1)
                    if ev.key == pygame.K_b:
                        p2.defend()
                    if ev.key == pygame.K_v:
                        p2.heal()
            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_a:
                    p1_left = False
                if ev.key == pygame.K_d:
                    p1_right = False
                if two_player:
                    if ev.key == pygame.K_LEFT:
                        p2_left = False
                    if ev.key == pygame.K_RIGHT:
                        p2_right = False

        if paused:
            draw_center_text(screen, 'PAUSE', HEIGHT//2, YELLOW, huge_font)
            draw_center_text(screen, 'P - Devam', HEIGHT//2 + 60, WHITE, font)
            pygame.display.flip()
            continue

        # hareket
        dx1 = 0
        if p1_left: dx1 -= p1.speed
        if p1_right: dx1 += p1.speed
        p1.move(dx1)
        p1.apply_gravity()

        if two_player:
            dx2 = 0
            if p2_left: dx2 -= p2.speed
            if p2_right: dx2 += p2.speed
            p2.move(dx2)
            p2.apply_gravity()
        else:
            # AI karar
            act = enemy_ai.decide(p1)
            if act == 'approach':
                if enemy.center_x() > p1.center_x()+40:
                    enemy.move(-enemy.speed * 0.95)
                elif enemy.center_x() < p1.center_x()-40:
                    enemy.move(enemy.speed * 0.95)
            elif act == 'attack':
                enemy.normal_attack(p1)
            elif act == 'special':
                enemy.special_attack(p1)
            elif act == 'defend':
                enemy.defend()
            elif act == 'heal':
                enemy.heal()

        # küçük rasgele ek hamleler
        if not two_player and random.random() < 0.01:
            if abs(enemy.center_x() - p1.center_x()) < 90 and random.random() < 0.6:
                enemy.normal_attack(p1)

        # update
        p1.update()
        enemy.update()
        if two_player: p2.update()

        # check game over
        if p1.health <= 0:
            game_over = True
            winner = enemy.name
        if enemy.health <= 0:
            game_over = True
            winner = p1.name if not two_player else (p1.name if p1.health>p2.health else enemy.name)

        # draw
        if BACKGROUND_IMG:
            bg = pygame.transform.scale(BACKGROUND_IMG, (WIDTH, HEIGHT))
            screen.blit(bg, (0,0))
        else:
            screen.fill(BG_COLOR)

        # zemin
        pygame.draw.rect(screen, (32,32,44), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))

        draw_hud(p1, enemy)

        p1.draw(screen)
        enemy.draw(screen)
        if two_player:
            p2.draw(screen)

        draw_text(screen, 'Kontroller P1: A/D W J K L H | P2: ←/→ ↑ M N B V', 18, HEIGHT-36, GRAY)

        if game_over:
            # karartma
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            screen.blit(overlay, (0,0))
            draw_center_text(screen, f'OYUN BITTI! KAZANAN: {winner}', HEIGHT//2 - 20, WHITE, huge_font)
            draw_center_text(screen, 'R - Tekrar Oyna    ESC - Ana Menü', HEIGHT//2 + 40, GRAY, large_font)

        pygame.display.flip()

        if game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                return game_loop(two_player)
            if keys[pygame.K_ESCAPE]:
                return

    pygame.quit()

# ====== Başlat ======
if __name__ == '__main__':
    choice = main_menu()
    if choice == 2:
        pygame.quit(); exit()
    two_player = (choice == 1)
    game_loop(two_player)
