from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random

# =====================
# global variables
# =====================
camera_pos = (0, 700, 700)
fovY = 120
GRID_LENGTH = 600
rand_var = 423

# =====================
#game state
# =====================
WIN_W, WIN_H = 1000, 800
TILE = 40.0
OUTER_WALL_H = 60.0
INNER_WALL_H = 40.0

W, H = 21, 21  # grid cells

# colors
GREEN = (0.0, 0.6, 0.0)
LIGHT_GREEN = (0.6, 0.9, 0.6)
ORANGE = (1.0, 0.6, 0.0)
PURPLE = (0.6, 0.0, 0.8)
CYAN = (0.0, 0.9, 1.0)
DARK_RED = (0.4, 0.0, 0.0)
DARK_GRAY = (0.25, 0.25, 0.25)
LIGHT_BLUE = (0.7, 0.9, 1.0)
YELLOW = (1.0, 1.0, 0.0)

# camera modes
CAM_TOP = 0
CAM_THIRD = 1
CAM_FIRST = 2

#adjustable camera parameters
cam_top_height = 600.0
cam_third_dist = 120.0
cam_third_height = 90.0
cam_orbit_angle = 0.0  # degrees, adjusted by left/right arrows


MOVE_STEP = 3.0          # Pac-Man forward/back per frame
TURN_STEP = 2.5          # degrees per frame
ENEMY_STEP = 2.2         # per frame
BULLET_STEP = 9.0
BULLET_RADIUS = 3.0
ENEMY_RADIUS = 10.0
PAC_RADIUS = 10.0
POWER_RADIUS = 6.0

BULLET_LIFE_FRAMES = 120
ENEMY_SPAWN_FRAMES = 240
POWER_SPAWN_FRAMES = 420
OBSTACLE_SPAWN_FRAMES = 300  # 5 seconds at 60fps
AUTO_SHOOT_RATE_FRAMES = 18

SPEED_BOOST_FRAMES = 300  # 5 seconds
AUTO_SHOOT_FRAMES = 300   # 5 seconds
SPEED_COOLDOWN_FRAMES = 600
AUTO_COOLDOWN_FRAMES = 720

# =====================
# Maze and State
# =====================
maze = [[0 for _ in range(W)] for __ in range(H)]
wall_segments = []

def build_cross_maze():

    # Clear maze
    for r in range(H):
        for c in range(W):
            maze[r][c] = 0
    
    #outer borders (walls)
    for r in range(H):
        maze[r][0] = 1
        maze[r][W-1] = 1
    for c in range(W):
        maze[0][c] = 1
        maze[H-1][c] = 1
    
    #cross pattern
    mr, mc = H//2, W//2
    for r in range(1, H-1):
        maze[r][mc] = 1
    for c in range(1, W-1):
        maze[mr][c] = 1
    
    #openings in the cross
    for d in (-2, 2):
        if 0 < mc+d < W-1:
            maze[mr][mc+d] = 0
        if 0 < mr+d < H-1:
            maze[mr+d][mc] = 0
    
    #inner blocks for complexity
    for r in range(3, H-3, 4):
        for c in range(3, W-3, 6):
            if maze[r][c] == 0:
                maze[r][c] = 1
                if c+1 < W-1:
                    maze[r][c+1] = 1

def rebuild_walls():

    wall_segments.clear()
    for r in range(H):
        for c in range(W):
            if maze[r][c] == 1:
                is_outer = (r in (0, H-1) or c in (0, W-1))
                wall_segments.append((r, c, is_outer))

def grid_to_world(rc):

    r, c = rc
    x = (c - W/2.0) * TILE + TILE/2.0
    y = (r - H/2.0) * TILE + TILE/2.0
    return x, y

def world_to_grid(x, y):

    c = int(round(x / TILE + W/2.0 - 0.5))
    r = int(round(y / TILE + H/2.0 - 0.5))
    return r, c

def passable(x, y):

    r, c = world_to_grid(x, y)
    if 0 <= r < H and 0 <= c < W:
        return maze[r][c] == 0
    return False

def collide2d(x1, y1, r1, x2, y2, r2):

    return (x1-x2)**2 + (y1-y2)**2 <= (r1+r2)**2

# =====================
#game Classes
# =====================
class PacMan:
    def __init__(self):
        self.x, self.y = grid_to_world((H-2, 1))
        self.z = PAC_RADIUS
        self.yaw = 0.0
        self.mv = 0     # -1 back, 0 idle, +1 forward
        self.turn = 0   # -1 left, 0 idle, +1 right

    def update(self):
        # Turning
        self.yaw += self.turn * TURN_STEP
        
        # Forward vector (XY plane, Z is up)
        rad = math.radians(self.yaw)
        fx, fy = math.cos(rad), math.sin(rad)
        
        # Speed boost multiplier
        speed_mult = 1.75 if game.speed_boost_active else 1.0
        step = MOVE_STEP * speed_mult
        
        # Calculate new position
        nx = self.x + fx * step * self.mv
        ny = self.y + fy * step * self.mv
        
        # Collision detection
        if passable(nx, self.y): 
            self.x = nx
        if passable(self.x, ny): 
            self.y = ny

    def draw(self):
        glColor3f(*ORANGE)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(90, 1, 0, 0)  # orient sphere upwards
        glutSolidSphere(PAC_RADIUS, 20, 16)
        
        # Add eyes to show direction
        glColor3f(0, 0, 0)  # Black eyes
        eye_offset = PAC_RADIUS * 0.6
        
        # Left eye
        glPushMatrix()
        glTranslatef(eye_offset, PAC_RADIUS * 0.3, PAC_RADIUS * 0.4)
        glutSolidSphere(2, 8, 6)
        glPopMatrix()
        
        # Right eye
        glPushMatrix()
        glTranslatef(eye_offset, -PAC_RADIUS * 0.3, PAC_RADIUS * 0.4)
        glutSolidSphere(2, 8, 6)
        glPopMatrix()
        
        glPopMatrix()

    def fire(self, target=None):

        rad = math.radians(self.yaw)
        dx, dy = math.cos(rad), math.sin(rad)
        
        if target is not None:
            tx, ty = target
            L = math.hypot(tx, ty) + 1e-6
            dx, dy = tx / L, ty / L
        
        bx = self.x + dx * (PAC_RADIUS + 4)
        by = self.y + dy * (PAC_RADIUS + 4)
        game.bullets.append(Bullet(bx, by, dx, dy))

class Bullet:
    def __init__(self, x, y, dx, dy):
        self.x, self.y = x, y
        self.z = PAC_RADIUS
        self.dx, self.dy = dx, dy
        self.life = BULLET_LIFE_FRAMES
        self.alive = True

    def update(self):
        if not self.alive: 
            return
            
        self.x += self.dx * BULLET_STEP
        self.y += self.dy * BULLET_STEP
        
        if not passable(self.x, self.y):
            self.alive = False
            
        self.life -= 1
        if self.life <= 0 and self.alive:
            self.alive = False
            game.bullets_missed += 1

    def draw(self):
        if not self.alive: 
            return
        glColor3f(*YELLOW)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(90, 1, 0, 0)
        glutSolidSphere(BULLET_RADIUS, 12, 8)
        glPopMatrix()

class Enemy:
    def __init__(self, r, c):
        self.x, self.y = grid_to_world((r, c))
        self.z = ENEMY_RADIUS
        self.alive = True

    def update(self):
        if not self.alive: 
            return
            
        #chasing Pac-Man
        dx = game.pac.x - self.x
        dy = game.pac.y - self.y
        L = math.hypot(dx, dy) + 1e-6
        vx = (dx / L) * ENEMY_STEP
        vy = (dy / L) * ENEMY_STEP
        
        nx, ny = self.x + vx, self.y + vy
        if passable(nx, self.y): 
            self.x = nx
        if passable(self.x, ny): 
            self.y = ny

    def draw(self):
        if not self.alive: 
            return
        glColor3f(*PURPLE)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(90, 1, 0, 0)
        glutSolidSphere(ENEMY_RADIUS, 20, 16)
        glPopMatrix()

class PowerUp:
    def __init__(self, r, c):
        self.r, self.c = r, c
        self.x, self.y = grid_to_world((r, c))

    def update(self):
        pass  

    def draw(self):

        s = 1.0 + 0.25 * math.sin(game.frame * 0.2)
        glPushMatrix()
        glColor3f(*CYAN)
        glTranslatef(self.x, self.y, POWER_RADIUS + 2)
        glScalef(s, s, s)
        glRotatef(90, 1, 0, 0)
        glutSolidSphere(POWER_RADIUS, 18, 14)
        glPopMatrix()

class FallingObstacle:
    def __init__(self, r, c):
        self.r, self.c = r, c
        self.x, self.y = grid_to_world((r, c))
        self.z = 220.0
        self.vz = 0.0
        self.landed = False

    def update(self):
        if self.landed: 
            return
            

        self.vz -= 2.5
        self.z += self.vz
        
        if self.z <= 0.0:
            self.z = 0.0
            self.landed = True

            if maze[self.r][self.c] == 0:
                maze[self.r][self.c] = -1

    def draw(self):
        glColor3f(*DARK_RED)
        glPushMatrix()
        glTranslatef(self.x, self.y, max(self.z, 8.0))
        glutSolidCube(16.0)
        glPopMatrix()

# =====================
#spawning 
# =====================
def random_floor_cell():

    tries = 0
    while tries < 500:
        r = random.randint(1, H-2)
        c = random.randint(1, W-2)
        if maze[r][c] == 0:
            px, py = game.pac.x, game.pac.y
            gx, gy = grid_to_world((r, c))
            if (px-gx)**2 + (py-gy)**2 > (TILE*2.0)**2:
                return (r, c)
        tries += 1
    return (1, 1)

def spawn_enemy():
    r, c = random_floor_cell()
    game.enemies.append(Enemy(r, c))

def spawn_power():
    r, c = random_floor_cell()
    game.powerups.append(PowerUp(r, c))

def spawn_obstacle():
    r, c = random_floor_cell()
    game.obstacles.append(FallingObstacle(r, c))

# =====================
# Game State
# =====================
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.lives = 3
        self.score = 0
        self.bullets_missed = 0
        self.paused = False
        self.game_over = False
        self.camera_mode = CAM_THIRD

        self.pac = PacMan()
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.obstacles = []

        self.frame = 0
        self.enemy_spawn_cnt = 0
        self.power_spawn_cnt = 0
        self.obstacle_spawn_cnt = 0

        # Special Abilities
        self.speed_boost_active = False
        self.speed_frames_left = 0
        self.speed_cd_left = 0

        self.auto_shoot_active = False
        self.auto_frames_left = 0
        self.auto_cd_left = 0
        self.auto_tick = 0

        # Rebuild maze
        build_cross_maze()
        rebuild_walls()

game = Game()


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):

    glColor3f(1.0, 1.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_maze():

    for (r, c, is_outer) in wall_segments:
        x, y = grid_to_world((r, c))
        h = OUTER_WALL_H if is_outer else INNER_WALL_H
        base = GREEN if is_outer else LIGHT_GREEN
        
        # Brick pattern: alternating darkness
        shade = 0.85 if ((r + c) % 2 == 0) else 0.65
        col = (min(1, base[0]*shade), min(1, base[1]*shade), min(1, base[2]*shade))
        
        glColor3f(*col)
        glPushMatrix()
        glTranslatef(x, y, h/2.0)
        glScalef(TILE, TILE, h)
        glutSolidCube(1.0)
        glPopMatrix()


    glColor3f(*DARK_GRAY)
    for r in range(H):
        for c in range(W):
            if maze[r][c] == -1:
                x, y = grid_to_world((r, c))
                s = TILE*0.9
                glBegin(GL_QUADS)
                glVertex3f(x - s/2, y - s/2, 1.0)
                glVertex3f(x + s/2, y - s/2, 1.0)
                glVertex3f(x + s/2, y + s/2, 1.0)
                glVertex3f(x - s/2, y + s/2, 1.0)
                glEnd()

def draw_hud():

    cam_name = {CAM_TOP: "Top", CAM_THIRD: "Third", CAM_FIRST: "First"}[game.camera_mode]
    draw_text(10, 770, f"Lives: {game.lives}  Score: {game.score}  Missed: {game.bullets_missed}  Cam: {cam_name}")
    
    if game.paused: 
        draw_text(10, 740, "Paused (P)")
    if game.game_over: 
        draw_text(10, 710, "GAME OVER (R to Restart)")
    if game.speed_boost_active: 
        draw_text(10, 680, f"Speed Boost ACTIVE ({game.speed_frames_left}f)")
    if game.auto_shoot_active: 
        draw_text(10, 650, f"Auto Shoot ACTIVE ({game.auto_frames_left}f)")
    if game.speed_cd_left > 0: 
        draw_text(10, 620, f"Speed CD: {game.speed_cd_left}f")
    if game.auto_cd_left > 0: 
        draw_text(10, 590, f"Auto CD: {game.auto_cd_left}f")

def draw_shapes():

    draw_maze()
    

    for o in game.obstacles: 
        o.draw()
    for p in game.powerups: 
        p.draw()
    for e in game.enemies: 
        e.draw()
    for b in game.bullets: 
        b.draw()
    

    game.pac.draw()

def draw_floor_plane():

    size = max(W, H) * TILE
    glColor3f(0.05, 0.05, 0.05)
    glBegin(GL_QUADS)
    glVertex3f(-size/2, -size/2, 0)
    glVertex3f( size/2, -size/2, 0)
    glVertex3f( size/2,  size/2, 0)
    glVertex3f(-size/2,  size/2, 0)
    glEnd()

# =====================
# Input handlers 
# =====================
def keyboardListener(key, x, y):

    if game.game_over:
        if key in (b'r', b'R'):
            game.reset()
        return

    # Pac-Man movement controls
    if key in (b'w', b'W'):
        game.pac.mv = 1
    elif key in (b's', b'S'):
        game.pac.mv = -1
    elif key in (b'a', b'A'):
        game.pac.turn = -1
    elif key in (b'd', b'D'):
        game.pac.turn = 1
    
    # Game controls
    elif key in (b'p', b'P'):
        game.paused = not game.paused
    elif key in (b'1',):
        game.camera_mode = CAM_TOP
    elif key in (b'2',):
        game.camera_mode = CAM_THIRD
    
    # Special abilities
    elif key == b' ':  # Space for speed boost
        if (not game.speed_boost_active) and game.speed_cd_left == 0:
            game.speed_boost_active = True
            game.speed_frames_left = SPEED_BOOST_FRAMES
    elif key in (b'c', b'C'):  # C for auto shoot
        if (not game.auto_shoot_active) and game.auto_cd_left == 0:
            game.auto_shoot_active = True
            game.auto_frames_left = AUTO_SHOOT_FRAMES
            game.auto_tick = 0
    
    # Restart
    elif key in (b'r', b'R'):
        game.reset()

    # Cheats
    elif key in (b'l', b'L'):
        game.lives = min(9, game.lives + 1)
    elif key in (b'k', b'K'):
        # eliminate all enemies
        for e in game.enemies:
            e.alive = False
    elif key in (b'g', b'G'):
        # toggle god mode (no life loss)
        game.god_mode = not getattr(game, 'god_mode', False)
    elif key in (b'+',):
        game.score += 50
    elif key in (b'e', b'E'):
        spawn_enemy()
    elif key in (b'u', b'U'):
        spawn_power()
    elif key in (b'o', b'O'):
        spawn_obstacle()
    elif key in (b'c',):

        pass
    elif key in (b'x', b'X'):
        # clear destroyed paths
        for r in range(H):
            for c in range(W):
                if maze[r][c] == -1:
                    maze[r][c] = 0

def keyboardListenerUp(key, x, y):

    if key in (b'w', b'W', b's', b'S'):
        game.pac.mv = 0
    if key in (b'a', b'A', b'd', b'D'):
        game.pac.turn = 0

def specialKeyListener(key, x, y):

    global cam_top_height, cam_third_height, cam_third_dist
    global cam_orbit_angle
    if key == GLUT_KEY_LEFT:
        cam_orbit_angle = (cam_orbit_angle - 4.0) % 360.0
    elif key == GLUT_KEY_RIGHT:
        cam_orbit_angle = (cam_orbit_angle + 4.0) % 360.0
    elif key == GLUT_KEY_UP:
        if game.camera_mode == CAM_TOP:
            cam_top_height = min(1500.0, cam_top_height + 30.0)
        elif game.camera_mode == CAM_THIRD:
            cam_third_height = min(220.0, cam_third_height + 6.0)
            cam_third_dist = min(300.0, cam_third_dist + 8.0)
    elif key == GLUT_KEY_DOWN:
        if game.camera_mode == CAM_TOP:
            cam_top_height = max(200.0, cam_top_height - 30.0)
        elif game.camera_mode == CAM_THIRD:
            cam_third_height = max(30.0, cam_third_height - 6.0)
            cam_third_dist = max(60.0, cam_third_dist - 8.0)

def mouseListener(button, state_btn, x, y):

    if button == GLUT_LEFT_BUTTON and state_btn == GLUT_DOWN:
        game.pac.fire(None)
    
    # Right mouse button cycles to first-person view
    if button == GLUT_RIGHT_BUTTON and state_btn == GLUT_DOWN:
        game.camera_mode = CAM_FIRST

# =====================
# Camera system 
# =====================
def setupCamera():

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, WIN_W/float(WIN_H), 0.1, 2000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    #eye/center based on camera mode
    if game.camera_mode == CAM_TOP:
        # Top-down view (adjustable height)
        ex, ey, ez = game.pac.x, game.pac.y, cam_top_height
        cx, cy, cz = game.pac.x, game.pac.y, 0.0
    elif game.camera_mode == CAM_FIRST:
        #FPV
        rad = math.radians(game.pac.yaw)
        dx, dy = math.cos(rad), math.sin(rad)
        ex, ey, ez = game.pac.x + dx*10.0, game.pac.y + dy*10.0, PAC_RADIUS*1.6
        cx, cy, cz = ex + dx*30.0, ey + dy*30.0, PAC_RADIUS*1.6
    else:  # CAM_THIRD
        #TPV
        rad = math.radians(game.pac.yaw + cam_orbit_angle)
        dx, dy = math.cos(rad), math.sin(rad)
        ex, ey, ez = game.pac.x - dx*cam_third_dist, game.pac.y - dy*cam_third_dist, cam_third_height
        cx, cy, cz = game.pac.x, game.pac.y, PAC_RADIUS

    gluLookAt(ex, ey, ez,  cx, cy, cz,  0, 0, 1)


def idle():

    if not game.paused and not game.game_over:
        # Spawning system
        game.enemy_spawn_cnt += 1
        game.power_spawn_cnt += 1
        game.obstacle_spawn_cnt += 1
        
        if game.enemy_spawn_cnt >= ENEMY_SPAWN_FRAMES:
            spawn_enemy()
            game.enemy_spawn_cnt = 0
        if game.power_spawn_cnt >= POWER_SPAWN_FRAMES:
            spawn_power()
            game.power_spawn_cnt = 0
        if game.obstacle_spawn_cnt >= OBSTACLE_SPAWN_FRAMES:
            spawn_obstacle()
            game.obstacle_spawn_cnt = 0

        # Special abilities management
        if game.speed_boost_active:
            game.speed_frames_left -= 1
            if game.speed_frames_left <= 0:
                game.speed_boost_active = False
                game.speed_cd_left = SPEED_COOLDOWN_FRAMES
        elif game.speed_cd_left > 0:
            game.speed_cd_left -= 1

        if game.auto_shoot_active:
            game.auto_frames_left -= 1
            game.auto_tick -= 1
            if game.auto_tick <= 0:
                # auto shoot toward nearest enemy
                target_dir = None
                if game.enemies:
                    alive_enemies = [e for e in game.enemies if e.alive]
                    if alive_enemies:
                        nearest = min(alive_enemies, key=lambda e: (game.pac.x-e.x)**2 + (game.pac.y-e.y)**2)
                        target_dir = (nearest.x - game.pac.x, nearest.y - game.pac.y)
                game.pac.fire(target_dir)
                game.auto_tick = AUTO_SHOOT_RATE_FRAMES
            if game.auto_frames_left <= 0:
                game.auto_shoot_active = False
                game.auto_cd_left = AUTO_COOLDOWN_FRAMES
        elif game.auto_cd_left > 0:
            game.auto_cd_left -= 1

        # Update all game objects
        game.pac.update()
        
        for b in game.bullets: 
            b.update()
        game.bullets = [b for b in game.bullets if b.alive]
        
        for e in game.enemies: 
            e.update()
        for p in game.powerups: 
            p.update()
        for o in game.obstacles: 
            o.update()

        # Collision detection
        # Bullets vs enemies
        for b in game.bullets:
            if not b.alive: 
                continue
            for e in game.enemies:
                if not e.alive: 
                    continue
                if collide2d(b.x, b.y, BULLET_RADIUS, e.x, e.y, ENEMY_RADIUS):
                    b.alive = False
                    e.alive = False
                    game.score += 10

        # Pac-Man vs enemies
        for e in game.enemies:
            if not e.alive: 
                continue
            if collide2d(game.pac.x, game.pac.y, PAC_RADIUS, e.x, e.y, ENEMY_RADIUS):
                e.alive = False
                if not getattr(game, 'god_mode', False):
                    game.lives -= 1
                if game.lives <= 0:
                    game.game_over = True

        # Pac-Man vs power-ups
        for p in game.powerups[:]:
            if collide2d(game.pac.x, game.pac.y, PAC_RADIUS, p.x, p.y, POWER_RADIUS + 2):
                game.lives = min(5, game.lives + 1)
                game.powerups.remove(p)

        game.frame += 1

    glutPostRedisplay()


def showScreen():

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)

    setupCamera()

    # Draw large floor plane for visibility
    draw_floor_plane()

    # Draw game world
    draw_shapes()
    draw_hud()

    glutSwapBuffers()


def run_game():

    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b'3D Pac-Man - Group 4')

    # OpenGL setup
    glClearColor(0.02, 0.02, 0.05, 1.0)
    glEnable(GL_DEPTH_TEST)

    # Register callbacks
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardListenerUp)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

run_game()
