from envwrapper import ConfigurationError, EnvWrapper, EnvVar
import os
import json
import io


import pytest


class Factory:
    pass


@pytest.fixture()
def os_env():
    old_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(old_env)


def test_init_dict():
    env = EnvWrapper(
        VAR={}
    )
    assert 'VAR' in env
    assert 'VAR' in dir(env)


def test_name_once():
    var = EnvVar()
    assert not var.name
    var.name = 'FOO'
    assert var.name == 'FOO'
    with pytest.raises(AssertionError) as e:
        var.name = 'BAR'
    assert str(e.value) == 'EnvVar name is immutable once set'


def test_get_item(os_env):
    env = EnvWrapper(DATA=EnvVar(convert=int))
    os_env['DATA'] = '1'
    assert env['DATA'] == 1


def test_name_mixed_case_error():
    var = EnvVar()
    with pytest.raises(AssertionError) as e:
        var.name = 'foo'
    assert str(e.value) == 'EnvVar name must be uppercase'


def test_empty_wrapper():
    env = EnvWrapper()
    assert len(list(dir(env))) == 0
    assert len(list(env.keys())) == 0


def test_len_keys_and_dir():
    env = EnvWrapper(
        VAR1=EnvVar(), VAR2=EnvVar()
    )
    assert set(env.keys()) == set(dir(env)) == {'VAR1', 'VAR2'}
    assert len(env) == len(dir(env)) == len(list(env.keys())) == 2


def test_items(os_env):
    env = EnvWrapper(
        VAR1=EnvVar(),
        VAR2=EnvVar()
    )
    os_env['VAR1'] = 'foo'
    os_env['VAR2'] = 'bar'
    d = dict(env.items())
    assert set(env.keys()) == set(d.keys())
    assert d['VAR1'] == 'foo'
    assert d['VAR2'] == 'bar'


def test_var_nocast(os_env):
    os_env['VAR1'] = 'some_value'
    env = EnvWrapper(VAR1=EnvVar())
    assert env.VAR1 == 'some_value'
    assert env['VAR1'] == 'some_value'
    assert env.get('VAR1') == 'some_value'


def test_var_bool(os_env):
    os_env['FLAG'] = 'on'
    env = EnvWrapper(FLAG=EnvVar(convert=bool))
    assert env.FLAG is True

    os_env['FLAG'] = '0'
    assert env.FLAG is False


def test_prefix(os_env):
    env = EnvWrapper(
        VAR=EnvVar(prefix='APP_')
    )
    os_env['APP_VAR'] = 'foo'
    assert 'VAR' in env.keys()
    assert 'APP_VAR' not in env


def test_default(os_env):
    os_env.setdefault('ENV', 'production')
    env = EnvWrapper(ENV=EnvVar(default='testing'))
    assert env.ENV == 'production'
    os_env.clear()
    assert env.ENV == 'testing'
    os_env['ENV'] = 'integration'
    assert env.ENV == 'integration'
    assert env.get('YADA') is None
    assert env.get('YADA', 'some_value') == 'some_value'


def test_preprocessor(os_env):
    env_ = EnvWrapper(
        DATA=EnvVar(preprocessor=str.lower, default='')
    )
    os_env['DATA'] = 'sOmE gARbaGE'
    assert env_.DATA == 'some garbage'


def test_import_class(os_env):
    os_env['FACTORY'] = __name__ + '.Factory'
    env = EnvWrapper(FACTORY=EnvVar(postprocessor=EnvVar.import_class))
    cls = env.get('FACTORY')
    assert cls
    assert isinstance(cls, type)


def test_import_error_module_not_found(os_env):
    os_env['FACTORY'] = 'tests.yada.SomeClass'
    env = EnvWrapper(FACTORY=EnvVar(postprocessor=EnvVar.import_class))
    with pytest.raises(ImportError) as e:
        _ = env.get('FACTORY')
    assert str(e.value) == "No module named 'tests.yada'"


def test_import_error_no_class(os_env):
    os_env['FACTORY'] = str(__name__) + '.SomeClass'
    env = EnvWrapper(FACTORY=EnvVar(postprocessor=EnvVar.import_class))
    with pytest.raises(ImportError) as e:
        _ = env.get('FACTORY')
    assert str(e.value) == f"No class named 'SomeClass' in module '{__name__}'"


def test_bundle(os_env):
    env = EnvWrapper(
        VAR1=EnvVar(bundle='VARS', preprocessor=str.upper),
        VAR2=EnvVar(bundle='VARS', preprocessor=str.upper)
    )
    assert 'VARS' in dir(env)
    assert 'VARS' in dict(env.items()).keys()
    assert 'VAR1' in dir(env)
    assert 'VAR2' in dir(env)

    os_env['VAR1'] = 'foo'
    os_env['VAR2'] = 'bar'
    d = env.VARS
    assert d == {
        'var1': 'FOO',
        'var2': 'BAR'
    }


def test_inclusion(os_env):
    env = EnvWrapper(
        FLAG=EnvVar(convert=bool),
        VAR1=EnvVar(include_if='FLAG')
    )
    os_env['VAR1'] = 'some_value'
    os_env['FLAG'] = 'on'
    assert 'VAR1' in dir(env)

    os_env['FLAG'] = 'off'
    assert 'VAR1' not in dir(env)


def test_exclusion(os_env):
    env = EnvWrapper(
        FLAG=EnvVar(convert=bool),
        VAR1=EnvVar(exclude_if='FLAG')
    )
    os_env['VAR1'] = 'some_value'
    os_env['FLAG'] = 'off'
    assert 'VAR1' in dir(env)

    os_env['FLAG'] = 'on'
    assert 'VAR1' not in dir(env)


def test_error_unknow_var():
    env = EnvWrapper()
    with pytest.raises(ConfigurationError) as e:
        _ = env._get('YADA')
    assert str(e.value) == 'Variable YADA is not declared ' \
                           'in this configuration'


def test_error_exclusion(os_env):
    env = EnvWrapper(
        FLAG=EnvVar(convert=bool),
        VAR1=EnvVar(exclude_if='FLAG')
    )
    os_env['VAR1'] = 'some_value'
    os_env['FLAG'] = 'on'
    with pytest.raises(ConfigurationError) as e:
        _ = env._get('VAR1')
    assert str(e.value) == 'Variable VAR1 is explicitly excluded ' \
                           'from this configuration'


def test_error_inclusion(os_env):
    env = EnvWrapper(
        FLAG=EnvVar(convert=bool),
        VAR1=EnvVar(include_if='FLAG')
    )
    os_env['VAR1'] = 'some_value'
    os_env['FLAG'] = 'off'
    with pytest.raises(ConfigurationError) as e:
        _ = env._get('VAR1')
    assert str(e.value) == 'Conditions to include variable VAR1 are not met'


def test_inc_exc_bundle(os_env):
    env = EnvWrapper(
        FLAG=EnvVar(convert=bool, bundle='SETTINGS'),
        VAR_1=EnvVar(include_if='FLAG', bundle='SETTINGS', default='foo'),
        VAR_2=EnvVar(exclude_if='FLAG', bundle='SETTINGS', default='bar')
    )
    os_env['FLAG'] = 'on'
    assert 'SETTINGS' in dir(env)
    assert 'FLAG' in dir(env)
    assert 'VAR_1' in dir(env)
    assert 'VAR_2' not in dir(env)
    assert 'flag' in env.get('SETTINGS')
    assert 'var_1' in env.get('SETTINGS')
    assert 'var_2' not in env.get('SETTINGS')

    os_env['FLAG'] = 'off'
    assert 'SETTINGS' in dir(env)
    assert 'FLAG' in dir(env)
    assert 'VAR_1' not in dir(env)
    assert 'VAR_2' in dir(env)
    assert 'flag' in env.get('SETTINGS')
    assert 'var_1' not in env.get('SETTINGS')
    assert 'var_2' in env.get('SETTINGS')


def test_inc_exc_error():
    with pytest.raises(ConfigurationError) as e:
        _ = EnvVar(include_if='REF1', exclude_if='REF1')

    assert str(e.value) == 'Cannot set both exclude_if and include_if ' \
                           'to the same name for an EnvVar instance'


def test_inc_exc(os_env):
    env = EnvWrapper(
        INC=EnvVar(convert=bool),
        EXC=EnvVar(convert=bool),
        VAR=EnvVar(include_if='INC', exclude_if='EXC')
    )
    os_env['INC'] = 'yes'
    os_env['EXC'] = 'no'
    os_env['VAR'] = 'foo'
    assert 'VAR' in env

    os_env['EXC'] = 'yes'
    assert 'VAR1' not in env

    os_env['EXC'] = 'no'
    os_env['INC'] = 'no'

    assert 'VAR1' not in env


def test_undeclared_ref():
    env_ = EnvWrapper(VAR1=EnvVar(include_if='VAR2', default='set'))
    with pytest.raises(ConfigurationError) as e:
        _ = env_.VAR1
    assert str(e.value) == 'Variable VAR2 is referenced but not declared'


def test_cast_to_bytes(os_env):
    env = EnvWrapper(
        DATA=EnvVar(convert=EnvVar.to_bytes, default='foo')
    )
    data = env.get('DATA')
    assert isinstance(data, bytes)
    assert data == bytes('foo', encoding='utf-8')


def test_collect():
    env = EnvWrapper(
        VAR=EnvVar(),
        PREFIXED=EnvVar(prefix='FOO_'),
        BUNDLED=EnvVar(bundle='GROUP'),
        PROXIED=EnvVar(proxy='YADA')
    )
    d = env.collect()
    expected_os_env = {'VAR', 'FOO_PREFIXED', 'BUNDLED', 'YADA'}
    assert set(d.keys()) == expected_os_env
    expected_app_schema = {
        'VAR', 'PREFIXED', 'GROUP', 'BUNDLED', 'PROXIED'
    }
    assert set(env.keys()) == expected_app_schema


def test_alt_bundle(os_env):
    env = EnvWrapper(
        SETTINGS=EnvVar(convert=dict)
    )
    d = {'foo': 0, 'bar': False, 'spam': "yada"}
    val = str(d)
    os_env['SETTINGS'] = val
    v = env.SETTINGS
    assert v == d
    assert env.collect()['SETTINGS'] == os_env['SETTINGS']


def test_proxy(os_env):
    env = EnvWrapper(
        PROXIED=EnvVar(proxy='PROXY')
    )
    os_env['PROXY'] = 'yada'
    assert env.PROXIED == 'yada'


def test_default_proxy(os_env):
    env = EnvWrapper(
        PROXIED=EnvVar(proxy='PROXY', default='yada')
    )
    os_env.clear()
    assert env.PROXIED == 'yada'


def test_json(os_env):
    env = EnvWrapper(
        JSON=EnvVar(postprocessor=json.loads)
    )
    expected = {
            'foo': 1, 'bar': 0.23
        }
    os_env['JSON'] = json.dumps(expected)
    actual = env.JSON
    assert actual == expected
    d = env.collect()
    assert d['JSON'] == os_env['JSON']


def test_iter_cast(os_env):
    env = EnvWrapper(
        NUMBERS=EnvVar(
            postprocessor=EnvVar.tokenize(sep=','),
            sub_cast=float
        )
    )
    os_env['NUMBERS'] = '0.1, 0.2, 0.3, 0.4'
    assert env.NUMBERS == [0.1, 0.2, 0.3, 0.4]
    d = env.collect()
    assert d['NUMBERS'] == os_env['NUMBERS']


def test_to_config(os_env):
    env = EnvWrapper(
        VAR=EnvVar(default='foo'),
        VAR1=EnvVar(bundle='SETTINGS', default='bar'),
        VAR2=EnvVar(bundle='SETTINGS', default='baz'),
        FLAG=EnvVar(convert=bool, default='no')
    )
    os_env.update(env.collect())
    f = io.StringIO()
    env.write_to_config(f, bool_values=('off', 'on'), preserve_case=False,
                        default_section='general')
    assert f.getvalue() == """[general]
var = foo
flag = off

[settings]
var1 = bar
var2 = baz

"""


def test_to_json(os_env):
    env = EnvWrapper(
        VAR=EnvVar(default='foo'),
        VAR1=EnvVar(bundle='SETTINGS', default='bar'),
        VAR2=EnvVar(bundle='SETTINGS', convert=bool, default='1'),
        FLAG=EnvVar(convert=bool, default='no')
    )
    os_env.update(env.collect())
    f = io.StringIO()
    env.write_to_json(f)
    assert f.getvalue() == '{"var": "foo", "flag": "false", ' \
                           '"settings": {"var1": "bar", "var2": "true"}}'

    f = io.StringIO()
    env.write_to_json(f, preserve_case=True)
    assert f.getvalue() == '{"VAR": "foo", "FLAG": "false", ' \
                           '"SETTINGS": {"VAR1": "bar", "VAR2": "true"}}'

    f = io.StringIO()
    env.write_to_json(f, sort_keys=True)
    assert f.getvalue() == '{"flag": "false", ' \
                           '"settings": {"var1": "bar", "var2": "true"}, ' \
                           '"var": "foo"}'


def test_to_source_file(os_env):
    env = EnvWrapper(
        VAR=EnvVar(default='foo'),
        VAR1=EnvVar(bundle='SETTINGS', default='bar'),
        VAR2=EnvVar(bundle='SETTINGS', convert=bool, default='1'),
        FLAG=EnvVar(convert=bool, default='no'),
        FAKE=EnvVar(proxy='YADA', default='yada')
    )
    os_env.update(env.collect())
    f = io.StringIO()
    env.write_to_source_file(f)
    assert f.getvalue() == """VAR=foo
VAR1=bar
VAR2=1
FLAG=no
YADA=yada
"""


def test_to_source_file_sorted(os_env):
    env = EnvWrapper(
        VAR=EnvVar(default='foo'),
        VAR1=EnvVar(bundle='SETTINGS', default='bar'),
        VAR2=EnvVar(bundle='SETTINGS', convert=bool, default='1'),
        FLAG=EnvVar(convert=bool, default='no'),
        FAKE=EnvVar(proxy='YADA', default='yada'),
        GRADE=EnvVar(default='AAA')
    )
    os_env.update(env.collect())
    f = io.StringIO()
    env.write_to_source_file(f, sort_keys=True)
    assert f.getvalue() == """FLAG=no
GRADE=AAA
VAR=foo
VAR1=bar
VAR2=1
YADA=yada
"""


def test_unknown_attribute():
    env = EnvWrapper()
    with pytest.raises(AttributeError) as e:
        _ = env.yada
    assert str(e.value) == "'EnvWrapper' object has no attribute 'yada'"


def test_get_as_dict():
    env = EnvWrapper()
    with pytest.raises(KeyError) as e:
        _ = env['yada']
    assert str(e.value) == "'yada'"


def test_get_as_object():
    env = EnvWrapper()
    with pytest.raises(AttributeError) as e:
        _ = env.YADA
    assert str(e.value) == "'EnvWrapper' object has no attribute 'YADA'"


def test_read_from_source_file():
    f = io.StringIO(
        """export foo='yada ' ;
        export flag=  ' on ';
        export switch='on';
        export var1  =' spam';
        export  var2='eg gs'  ;
        export workers=16;
        export boost=0.2;
        garbled: 'sh'pam'
        """
    )
    env = EnvWrapper.read_from_source_file(f, inline_prefix='export',
                                           inline_suffix=';',
                                           value_delimiter='\'',
                                           bool_values=('off', 'on'))
    assert all(('FOO' in env, 'FLAG' in env, 'VAR1' in env, 'VAR2' in env))
    assert env.FOO == 'yada '
    assert env.FLAG == ' on '
    assert not isinstance(env.FLAG, bool)
    assert env.VAR1 == ' spam'
    assert env.VAR2 == 'eg gs'
    assert env.SWITCH is True
    assert env.WORKERS == int('16')
    assert env.BOOST == float('0.2')
    assert 'GARBLED' not in env


def test_read_from_source_file_undelimited_values():
    f = io.StringIO(
        """ foo: yada
         flag:   off
         var1  :spam
         garbled: sh'pam
          var2: eg gs
          var3: 42
          var4: 7.09
        """
    )
    env = EnvWrapper.read_from_source_file(f, delimiter=':',
                                           bool_values=('off', 'on'))
    assert all(('FOO' in env, 'FLAG' in env, 'VAR1' in env, 'VAR2' in env))
    assert env.VAR2 == 'eg gs'
    assert env.FLAG is False
    assert env.GARBLED == 'sh\'pam'
    assert env.VAR3 == int('42')
    assert env.VAR4 == float('7.09')


def test_read_from_json():
    f = io.StringIO('{"flag": "false", '
                    '"settings": {"var1": "bar", "var2": "true"}, '
                    '"var": "foo"}'
                    )
    env = EnvWrapper.read_from_json(f)
    assert all(('FLAG' in env, 'VAR' in env, 'VAR1' in env, 'VAR2' in env))
    assert 'SETTINGS' in env


def test_read_from_config():
    f = io.StringIO("""[general]
var = foo
FLAG = off

[settings]
var1 = bar
var2 = baz

"""
                    )
    env = EnvWrapper.read_from_config(f, default_section='general',
                                      bool_values=('off', 'on'))
    assert all(('FLAG' in env, 'VAR' in env, 'VAR1' in env, 'VAR2' in env))
    assert 'SETTINGS' in env


def test_proxy_def(os_env):
    env = EnvWrapper(VAR1=EnvVar(default='foo', proxy='OS_VAR1'))
    os_env.setdefault('VAR1', 'yada')
    os_env.setdefault('OS_VAR1', 'spam')
    assert env.VAR1 == 'spam'
    del os_env['OS_VAR1']
    assert env.VAR1 == 'foo'
