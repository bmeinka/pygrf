import pytest
from math import isclose


from pygrf import open_act


@pytest.mark.parametrize('name, version', (
    ('cursors.act', 0x203),
    ('agav.act', 0x205),
))
def test_act_has_correct_version(data_files, name, version):
    act = open_act(data_files[name])
    assert act.version == version


@pytest.mark.parametrize('name, count', (
    ('cursors.act', 13),
    ('agav.act', 40),
))
def test_act_has_correct_animation_count(data_files, name, count):
    act = open_act(data_files[name])
    assert len(act.animations) == count


@pytest.mark.parametrize('name, count', (
    ('cursors.act', 0),
    ('agav.act', 5),
))
def test_act_has_correct_trigger_count(data_files, name, count):
    act = open_act(data_files[name])
    assert len(act.triggers) == count


def test_act_has_correct_triggers(data_files):
    act = open_act(data_files['agav.act'])
    triggers = (
        "vanberk_move.wav",
        "vanberk_attack.wav",
        "vanberk_damage.wav",
        "vanberk_die.wav",
        "atk",
    )
    for idx, trigger in enumerate(triggers):
        assert act.triggers[idx] == trigger


@pytest.mark.parametrize('name, interval', (
    ('cursors.act', 2.0),
    ('agav.act', 4.0),
))
def test_act_animation_has_correct_interval(data_files, name, interval):
    act = open_act(data_files[name])
    assert act.animations[0].interval == interval


@pytest.mark.parametrize('name, counts', (
    ('cursors.act', (11, 9, 3)),
    ('agav.act', (4, 4, 4)),
))
def test_act_animation_has_correct_frame_count(data_files, name, counts):
    act = open_act(data_files[name])
    assert len(act.animations[0].frames) == counts[0]
    assert len(act.animations[1].frames) == counts[1]
    assert len(act.animations[2].frames) == counts[2]


def test_act_frame_has_correct_layer_count(data_files):
    act = open_act(data_files['cursors.act'])
    assert len(act.animations[0].frames[0].layers) == 1
    assert len(act.animations[1].frames[8].layers) == 4


def test_act_frame_has_correct_trigger_id(data_files):
    act = open_act(data_files['agav.act'])
    assert act.animations[0].frames[0].trigger == -1
    assert act.animations[8].frames[7].trigger == 0


def test_act_layer_has_correct_position(data_files):
    act = open_act(data_files['cursors.act'])
    assert act.animations[0].frames[0].layers[0].offset == (11, 15)
    assert act.animations[1].frames[1].layers[0].offset == (0, -1)


def test_act_layer_has_correct_index(data_files):
    act = open_act(data_files['cursors.act'])
    assert act.animations[0].frames[0].layers[0].index == 0
    assert act.animations[1].frames[1].layers[0].index == 16


@pytest.mark.parametrize('name, flipped', (
    ('cursors.act', False),
    ('agav.act', True),
))
def test_act_layer_is_correctly_flipped(data_files, name, flipped):
    act = open_act(data_files[name])
    assert act.animations[0].frames[0].layers[0].flipped == flipped


@pytest.mark.parametrize('name, color', (
    ('cursors.act', (255, 255, 255, 245)),
    ('agav.act', (255, 255, 255, 255)),
))
def test_act_layer_has_correct_color(data_files, name, color):
    act = open_act(data_files[name])
    assert act.animations[0].frames[0].layers[0].color == color


def test_act_layer_has_correct_zoom(data_files):
    act = open_act(data_files['cursors.act'])
    assert act.animations[0].frames[0].layers[0].zoom == (1.0, 1.0)
    zoom = act.animations[1].frames[1].layers[0].zoom
    assert isclose(zoom.x, 1.2, abs_tol=0.0001)
    assert isclose(zoom.y, 1.2, abs_tol=0.0001)


def test_act_layer_has_correct_angle(data_files):
    act = open_act(data_files['agav.act'])
    assert act.animations[0].frames[0].layers[0].angle == 0.0
    angle = act.animations[24].frames[3].layers[0].angle
    assert isclose(angle, 2.8026e-45, rel_tol=0.00001)