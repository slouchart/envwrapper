EnvWrapper: A wrapper around OS environment variables accessed through `os.environ`


# Motivation
Configuration applications with respect to 12-factor guidelines can be
cumbersome and ugly. On the other hand, wrapping os.environ so that
environment variables (envvars) start to behave as actual types instead of being just
string serializations is desired. Hence this package, aptly and unimaginatively
named `envwrapper`

# Features
## Declaring envvars as mapping items at initialisation
``` python
>>> env = EnvWrapper(MY_VAR1=EnvVar(), MY_VAR2=EnvVar())
```

An instance of EnvWrapper appears as a subset of os.environ

## Specifying type conversion primitives
``` python
>>> env = EnvWrapper(FLAG=EnvVar(convert=bool), NUMBER=EnvVar(convert=int), VALUE=EnvVar(convert=float))
```
Accessing `env.FLAG`, `env.NUMBER` or `env.VALUE` returns a `bool`, an `int` or a `float` respectively


## Using prefixed and 'proxied' envvars

Suppose you need to isolate some of your variables from the other envvars but
you need to retain the original name e.g. `ENV` (as required by Flask apps) in
your app but the name `MY_APP_ENV` is required to be in the environment.

Declaring an environment wrapper the following way does the trick:
``` python
>>> env = EnvWrapper(ENV=EnvVar(prefix='MY_APP_'))
```

Suppose now a specific variable named `FOO` is present in the environment with
a value that suits the needs of your app. However, the internal naming scheme
of your app required this envvar to be named `BAR`.

Declare your variable as a proxy:
``` python
>>> env = EnvWrapper(BAR=EnvVar(proxy='FOO'))
```

## Dealing with default values

`os.environ` comes with a `setdefault` method which may have an Action at a Distance effect, especially if your app
needs more than one set of envvars or two envvars sharing the same name but with different default values.

`envwrapper` allows you to specify a default string value for an envvar at declaration:
``` python
>>> env = EnvWrapper(VAR1=EnvVar(default='foo'))
```

This value takes precedence over any default value set for the underlying `os.environ` key.
In the case of a 'proxied' envvar, though, the default value set at `os.environ` level takes precedence
as illustrated in the sequence of code below:

``` python
>>> env = EnvWrapper(VAR1=EnvVar(default='foo', proxy='OS_VAR1'))
>>> os.environ.setdefault('VAR1', 'yada')
>>> os.environ.setdefault('OS_VAR1', 'spam')
>>> print(env.VAR1)
spam

>>> del os.environ['OS_VAR1']
>>> print(env.VAR1)
foo

```


## Working with bundles

Suppose some class in your app needs some  `**settings` to initialize a new instance.
Typically, you would code something like this if the values are to be found in
the environment:
``` python
>>> o = MyClass(foo=env.FOO, spam=env.SPAM)
```

This code tends to become chatty and cumbersome if the number of arguments is large (and by large, we mean greater than 3).
Instead of passing each argument individually from the env to the class `__init__` method, you may want to 'bundle' these variables
in a mapping and initialize this instance this way:
``` python
>>> o = MyClass(**env.MY_CLASS_SETTINGS)
```

Here comes the bundle feature to the rescue:
``` python
>>> env = EnvWrapper(FOO=EnvVar(bundle='MY_CLASS_SETTINGS'), SPAM=EnvVar(bundle='MY_CLASS_SETTINGS'))
>>> print(str(env.MY_CLASS_SETTINGS))
{
  'foo': 'bar',
  'spam': 'eggs'
}
```

A bundle basically collects all envvars marked as 'bundled' under its name into a dict keyed by envvars names in lowercase.
Note that unbundled variables are still available:
``` python
>>> print(env.FOO, env.SPAM)
bar eggs

```

## Conditionally excluding/including envvars
You can tailor the exposed envvar interface of an EnvWrapper by specifying the conditions under which some variables are included or excluded.
Suppose for instance that the variable FOO must be excluded if the variable FLAG is on and, on the other hand, the variable SPAM must be included
if the same variable is on.
``` python
>>> env = EnvWrapper(FLAG=EnvVar(convert=bool, default='on'), FOO=EnvVar(exclude_if='FLAG'), SPAM=EnvVar(include_if='FLAG'))
>>> os.environ['FLAG'] = 'on'
>>> print(dir(env))
['FLAG', 'SPAM']
>>> os.environ['FLAG'] = 'off'
>>> print(dir(env))
['FLAG', 'FOO']

```

Conditional inclusion and exclusion work with bundled variables too.
``` python
>>> env = EnvWrapper(FLAG=EnvVar(convert=bool, default='on'), FOO=EnvVar(exclude_if='FLAG', bundle='CIRCUS'), SPAM=EnvVar(include_if='FLAG', bundle='CIRCUS'))
>>> os.environ['FLAG'] = 'on'
>>> print(env.CIRCUS)
{'spam': ''}
>>> os.environ['FLAG'] = 'off'
>>> print(env.CIRCUS)
{'foo': ''}

```

# Preprocessing, postprocessing envvar values
Imagine you want to lowercase the value of an envvar.
``` python
>>> env = EnvWrapper(FOO=EnvVar(preprocessor=str.lower)
>>> os.environ['FOO'] = 'BAR'
>>> print(env.FOO)
bar
```

Now, for something completely different, suppose you need to tell your app to
use a certain class in some package at runtime (a.k.a. Poor man's dependency injection):
``` python
>>> env = EnvWrapper(FACTORY=EnvVar(postprocessor=EnvVar.import_class))
>>> os.environ['FACTORY'] = 'my_app.my_package.SomeClass'
>>> print(env.FACTORY)
<class 'my_app.my_package.SomeClass'>
```

Or, as a conclusion, you need to change the separator of a float and divide its value by 10 because some funny French guy messed around with its math:
``` python
>>> env = EnvWrapper(PI=EnvVar(default='31,4', convert=float, preprocessor=lambda s: s.translate(s.maketrans(',', '.')), postprocessor=lambda f: round(f/10.0, 2))
>>> print(env.PI)
3.14
```


# Dealing with iterables
Suppose some envvar contains a value such as `'1 2 3 4 5'` and you need to parse it as a list of integers.
`envwrapper` offers you in addition of pre- and postprocessor a way to 'subcast' each element of any iterable
computed by a postprocessor. Let's deal with that:
``` python
>>> env = EnvWrapper(VALUES=EnvVar(postprocessor=EnvVar.tokenize(), sub_cast=int))
>>> os.environ['VALUES'] = '1 2 3 4 5'
>>> print(env.VALUES)
[1, 2, 3, 4, 5]

```

On the other hand, you may have an envvar that contains a Python literal evaluating to a dict, a tuple or a list:
``` python
>>> env = EnvWrapper(VALUES=EnvVar(convert=tuple, sub_cast=int))
>>> os.environ['VALUES'] = "('1', '2', '3')"
>>> print(env.VALUES)
(1, 2, 3)

>>> env = EnvWrapper(VALUES=EnvVar(convert=dict, sub_cast=int))
>>> os.environ['VALUES'] = "{'foo': '1', 'bar': '2', 'spam': '3'}"
>>> print(env.VALUES)
{'bar': 2, 'foo': 1, 'spam': 3}

```

# Codecs interface
For those of you who are not that familiar with 12-factor app best practices or, for some reasons, do not want to implement them,
the `EnvWrapper` is able to read from and write your common configuration file formats.

The interface for doing so is rather self-explaining and I let the reader browse
the code relative to methods named `to_<stuff>` and the class methods named `from_<stuff>`

I nevertheless strongly recommend these readers to use the OS environment as a repository for configuration as files are pesky things that
are prone to not be at the location we expect them to be.

# Acknowledgments
I'd like to thank Phil Schleihauf (uniphil@gmail.com) and Rick Harris (rconradharris@gmail.com) for their respective contributions
to the art if dealing with configuration the 12-factor's way. Their own modules, `flask-environ` and `envparse` inspired me a lot and
some of their aspects are included in my own proposal.

# Further reading
[Configuring an application the 12-factor's way](https://12factor.net/config)
[Phil's `flask-environ`](https://github.com/uniphil/flask-environ)
[Rick's `envparse`](https://github.com/rconradharris/envparse)
