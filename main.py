from random import choice

import pygame, math
from pygame.locals import *
from enum import IntEnum
from math import sqrt


def combine_lists(l1, l2, sign):
    l1 = list(l1)
    for i in range(2):
        if sign == '+':
            l1[i] += l2[i]
        elif sign == '-':
            l1[i] -= l2[i]
        elif sign == '*':
            l1[i] *= l2[i]
        else:
            l1[i] /= l2[i]
    return l1


def convert_from_grid(grid_coordinates):
    return combine_lists(grid_coordinates, (grid_size, grid_size), '*')


def convert_to_grid(coordinates):
    return tuple([int((coordinates[i] - (coordinates[i] % grid_size)) / grid_size) for i in range(2)])


def find_all_grid_coordinates(coordinates, dimensions):
    start = convert_to_grid(coordinates)
    end = convert_to_grid(combine_lists(combine_lists(coordinates, dimensions, '+'), (1, 1), '-'))
    all_coordinates = []

    for x in range(start[0], end[0] + 1):
        for y in range(start[1], end[1] + 1):
            all_coordinates.append((x, y))

    return all_coordinates


def opposite(n):
    return abs(n - 1)


def find_center(d1, d2, c1=(0, 0)):
    return [(c1[i] + (d1[i] / 2 - d2[i] / 2)) for i in range(2)]


def make_tuple(thing):
    if type(thing) not in (list, tuple):
        return (thing,)
    return thing


def collision(c1, d1, c2, d2, inside_only=False):
    d1 = list(d1)
    d2 = list(d2)
    collisions = [False, False]
    for i in range(2):
        d1[i] -= 1
        d2[i] -= 1
        if (c1[i] <= c2[i] and c1[i] + d1[i] >= c2[i] + d2[i]) or \
                (c1[i] >= c2[i] and c1[i] + d1[i] <= c2[i] + d2[i]):
            collisions[i] = True
        if not inside_only:
            if (c2[i] <= c1[i] <= c2[i] + d2[i]) or \
                    (c2[i] <= c1[i] + d1[i] <= c2[i] + d2[i]):
                collisions[i] = True
    if False not in collisions:
        return True
    elif True in collisions:
        return collisions.index(False)


class SpriteSheet:
    def __init__(self, filename, division_index=1):
        self.sheet = pygame.image.load(filename).convert_alpha()
        self.division_index = division_index
        self.farthest_y_coordinate = 0

    def get_image(self, coordinates, dimensions):
        image = pygame.Surface(dimensions, SRCALPHA).convert_alpha()
        image.blit(self.sheet, (0, 0), (coordinates, dimensions))
        return image

    def get_sprites(self, starting_x_coordinate=0, farthest_y_coordinate=None, all_dimensions=None, y_constant=None,
                    x_constant=None, update=True, scale=3, block_number=None, dimensions=None):
        sprites = []
        if block_number:
            y_constant = tile_size
            x_constant = (tile_size, block_number)
        elif dimensions:
            y_constant = dimensions[1]
            x_constant = (dimensions[0], 1)

        if not farthest_y_coordinate:
            farthest_y_coordinate = self.farthest_y_coordinate
        if x_constant:
            thing = x_constant[1]
        else:
            thing = len(all_dimensions)
        farthest_x_coordinate = starting_x_coordinate

        for i in range(thing):
            coordinates = [0, 0]
            coordinates[opposite(self.division_index)] = farthest_x_coordinate
            coordinates[self.division_index] = farthest_y_coordinate

            dimensions = [0, 0]
            if x_constant or y_constant:
                if x_constant:
                    dimensions[opposite(self.division_index)] = x_constant[0]
                else:
                    dimensions[opposite(self.division_index)] = all_dimensions[i]
                if y_constant:
                    dimensions[self.division_index] = y_constant
                else:
                    dimensions[self.division_index] = all_dimensions[i]
            else:
                dimensions = all_dimensions[i]

            farthest_x_coordinate += dimensions[opposite(self.division_index)]
            sprite = self.get_image(coordinates, dimensions)
            if scale:
                sprite = pygame.transform.scale(sprite, combine_lists(sprite.get_size(),
                                                                      (scale, scale), '*'))
            sprites.append(sprite)

        if update:
            if y_constant:
                self.farthest_y_coordinate += y_constant
            elif x_constant:
                self.farthest_y_coordinate += max(all_dimensions)
            else:
                self.farthest_y_coordinate += max(
                    [dimensions[self.division_index] for dimensions in all_dimensions])

        return sprites


class Room:
    def __init__(self, map_sheet):
        self.map_sheet = map_sheet

    def get_color(self, coordinates):
        try:
            return tuple(self.map_sheet.get_at(coordinates))
        except:
            return 0, 0, 0, 0

    def generate(self):
        tiles = {}

        for x in range(self.map_sheet.get_width()):
            for y in range(self.map_sheet.get_height()):
                tile_color = self.get_color((x, y))
                print(tile_color)
                if tile_color[3] == 255:
                    print(1)
                    formatted_color = (tile_color[0], tile_color[1])
                    if formatted_color in room_tile_color_values:
                        block_type = room_tile_color_values[formatted_color]
                        tiles[(x, y)] = block_type
                    else:
                        raise Exception("Unidentified block_color {0} at {1}".format(color, (x, y)))

        for x in (-1, self.map_sheet.get_width() - 2):
            for y in range(-1, self.map_sheet.get_height() - 1):
                tiles[(x, y)] = RoomTileTypes.wall
        for y in (-1, self.map_sheet.get_height() - 2):
            for x in range(self.map_sheet.get_width() - 2):
                tiles[(x, y)] = RoomTileTypes.wall

        self.tiles = {}
        for initial_coordinates in tiles:
            tile_type = tiles[initial_coordinates]
            self.tiles[initial_coordinates] = Tile(tile_type, room_tile_sprites[tile_type],
                                                   convert_from_grid(initial_coordinates))


class Thing:
    def __init__(self, sprites, coordinates=(0, 0)):
        self.sprites = sprites
        self.coordinates = list(coordinates)
        self.reset()
        self.dimensions = self.current_sprite().get_size()
        self.all_grid_coordinates = find_all_grid_coordinates(self.coordinates, self.dimensions)

    def update_sprites(self, speed=4, reset=True):
        self.sprite_count += 1
        if self.sprite_count == speed:
            self.sprite_count = 0
            if self.sprite_index == len(self.current_sprites()) - 1:
                if reset:
                    self.sprite_index = 0
                return 'completed'
            self.sprite_index += 1

    def current_sprites(self):
        return make_tuple(self.sprites)

    def current_sprite(self):
        return self.current_sprites()[self.sprite_index]

    def reset(self):
        self.sprite_count = 0
        self.sprite_index = 0

    def update_grid_coordinates(self):
        self.all_grid_coordinates = find_all_grid_coordinates(self.coordinates, self.dimensions)


class Tile(Thing):
    def __init__(self, tile_type, sprites, coordinates):
        super().__init__(sprites, coordinates=coordinates)
        self.tile_type = tile_type


class Mob(Thing):
    def __init__(self, sprites, coordinates):
        self.direction = [1, 0]
        super().__init__(sprites, coordinates)
        self.velocity = [0, 0]

    def current_sprite(self):
        sprite = super().current_sprite()
        if self.direction == Directions.up:
            return pygame.toransform.rotate(sprite, 270)
        elif self.direction == Directions.right:
            return pygame.transform.rotate(sprite, 180)
        elif self.direction == Directions.down:
            return pygame.transform.rotate(sprite, 90)
        return sprite

    def combined_coordinates(self):
        return combine_lists(self.coordinates, self.velocity, '+')

    def process_collision(self, thing):
        for i in range(2):
            velocity = [0, 0]
            velocity[i] = self.velocity[i]
            print(i, velocity)
            if collision(combine_lists(self.coordinates, velocity, '+'), self.dimensions,
                         thing.coordinates, thing.dimensions) is True:
                print("collided")
                self.align_velocity(thing, i)

    def align_velocity(self, thing, i):
        if self.velocity[i] > 0:
            self.velocity[i] = thing.coordinates[i] - (
                self.coordinates[i] + self.dimensions[i])
        elif self.velocity[i] < 0:
            self.velocity[i] = (thing.coordinates[i] + thing.dimensions[i]) - \
                               self.coordinates[i]

    def update_grid_coordinates(self, velocity=True):
        if velocity:
            coordinates = self.combined_coordinates()
        else:
            coordinates = self.coordinates
        self.all_grid_coordinates = find_all_grid_coordinates(coordinates, self.dimensions)


class Player(Mob):
    def __init__(self, sprites, coordinates, movement_keys, movement_speed):
        super().__init__(sprites, coordinates)
        self.movement_keys = movement_keys
        self.movement_speed = movement_speed
        self.diagonal_movement_speed = int(self.movement_speed / sqrt(2))
        self.movement_direction = [0, 0]
        self.current_room = None
        self.fake_coordinates = find_center(screen_dimensions, self.dimensions)

    def generate_display_coordinates(self, coordinates):
        return combine_lists(
            combine_lists(coordinates, self.fake_coordinates, '+'),
            self.coordinates, '-')
        self.buls = []
        self.degree = 0
def pta(x, y, mx, my):
    if (x > mx):
        return 3.14 + math.atan((my - y)/(mx - x))
    else:
        return math.atan((my - y)/(mx - x))
class Bullet(Thing):
    def __init__(self, sprite, coordinates, angle):
        super().__init__(sprite, coordinates)
        self.angle = angle
    def move(self):
        self.x += math.cos(self.angle) * bul_speed
        self.y -= math.sin(self.angle) * bul_speed


class RoomTileTypes(IntEnum):
    wall = 0
    floor = 1
    entrance = 2
    exit = 3


class RoomTileClasses(IntEnum):
    solid = 0


class Keys(IntEnum):
    left = 0
    up = 1
    right = 2
    down = 3
    shoot = 4


class Directions(IntEnum):
    left = 0
    up = 1
    right = 2
    down = 3


scale_factor = 3
tile_size = 12
grid_size = scale_factor * tile_size
game_speed = 30
bul_speed = 8

screen_dimensions = (1080, 1080)
display = pygame.display.set_mode(screen_dimensions)
clock = pygame.time.Clock()

sprite_sheet = SpriteSheet("Sprite_Sheet.png")

player_sprites = sprite_sheet.get_sprites(block_number=4)
room_tile_sprites = sprite_sheet.get_sprites(block_number=4)

room_map_sheet = SpriteSheet("Level_Map_Sheet.png", )
room_maps = room_map_sheet.get_sprites(block_number=1, scale=1)

room_tile_color_values = {
    (51, 0): RoomTileTypes.wall,
    (102, 0): RoomTileTypes.entrance,
    (153, 0): RoomTileTypes.exit,
    (204, 0): RoomTileTypes.floor
}

tile_types = {
    RoomTileClasses.solid: (RoomTileTypes.wall,)
}


room = Room(room_maps[0])
room.generate()

player = Player(player_sprites, (0, 0), (K_LEFT, K_UP, K_RIGHT, K_DOWN), 6)
player.current_room = room

while True:
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            quit()
        if event.type == KEYDOWN and event.key == K_z:
            if game_speed == 30:
                game_speed = 1
            else:
                game_speed = 30

    player.velocity = [0, 0]

    for event in events:
        if event.type == KEYDOWN:
            if event.key == player.movement_keys[Keys.left]:
                player.direction = Directions.left
            elif event.key == player.movement_keys[Keys.right]:
                player.direction = Directions.right
            elif event.key == player.movement_keys[Keys.up]:
                player.direction = Directions.up
            elif event.key == player.movement_keys[Keys.down]:
                player.direction = Directions.down
        if event.type == MOUSEBUTTONUP:
            Player.buls.append(Bullet(bul_sprite, (player.coordinates[0], player.coordinates[1]), pta(player.coordinates[0], player.coordinates[1], event.pos[0], event.pos[1])))

    keys = pygame.key.get_pressed()
    if keys[player.movement_keys[Keys.left]]:
        player.movement_direction[0] = -1
    elif keys[player.movement_keys[Keys.right]]:
        player.movement_direction[0] = 1
    else:
        player.movement_direction[0] = 0

    if keys[player.movement_keys[Keys.up]]:
        player.movement_direction[1] = -1
    elif keys[player.movement_keys[Keys.down]]:
        player.movement_direction[1] = 1
    else:
        player.movement_direction[1] = 0

    if 0 not in player.movement_direction:
        speed = player.diagonal_movement_speed
    else:
        speed = player.movement_speed
    for bul in player.buls:
        bul.move()
    for i in range(2):
        if player.movement_direction[i] != 0:
            player.velocity[i] = speed * player.movement_direction[i]

    player.update_grid_coordinates()
    collided_object = None

    for grid_coordinates in player.all_grid_coordinates:
        tile = player.current_room.tiles[grid_coordinates]
        if tile.tile_type in tile_types[RoomTileClasses.solid]:
            if collision(player.combined_coordinates(), player.dimensions, tile.coordinates,
                         tile.dimensions) is True:
                collided_object = tile
                player.process_collision(collided_object)

    player.coordinates = player.combined_coordinates()

    display.fill(pygame.Color("white"))

    for tile in room.tiles:
        display.blit(room.tiles[tile].current_sprite(), player.generate_display_coordinates(room.tiles[tile].coordinates))

    display.blit(player.current_sprite(), player.fake_coordinates)

    pygame.display.update()
    clock.tick(game_speed)
