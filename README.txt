# Motivation
Configuration applications with respect to 12-factor guidelines can be
cumbersome and ugly. On the other hand, wrapping os.environ so that
environment variables (envvars) start to behave as actual types instead of being just
string serializations is desired. Hence this package. Aptly and unimaginatively
name `envwrapper`

# Features
## Declare envvars as mapping items at initialisation
``` python
>>> env = EnvWrapper(MY_VAR1=EnvVar(), MY_VAR2=EnvVar())
```

An instance of EnvWrapper appears as a subset of os.environ

## Specify type conversion primitives
``` python
>>> env = EnvWrapper(FLAG=EnvVar(convert=bool), NUMBER=EnvVar(convert=int), VALUE=EnvVar(convert=float))
```
Accessing `env.FLAG`, `env.NUMBER` or `env.VALUE` returns a `bool`, an `int` or a `float` respectively


## Prefixed and 'proxied' envvars

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

## Default values

`os.environ` comes with a `setdefault` method which may have an Action at a Distance effect, especially if your app
needs more than one set of envvars or two envvars sharing the same name but with different default values.

`envwrapper` allows you to specify a default string value for an envvar at declaration:
``` python
>>> env = EnvWrapper(VAR1=EnvVar(default='foo'))
```

This value takes precedence over any default value set for the underlying `os.environ` key.
In the case of a 'proxied' envvar, though, the default value set at `os.environ` level takes precedence
as illustrated in the sequence of code below

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
