# -*- coding: utf-8 -*-

__author__ = "Yuan Chang"
__copyright__ = "Copyright (C) 2019-2020"
__license__ = "MIT"
__email__ = "pyslvs@gmail.com"

from typing import (
    cast, get_type_hints, overload, TypeVar, List, Sequence, Dict, Mapping,
    Union, Type, Any,
)
from abc import ABCMeta
from dataclasses import dataclass, field, is_dataclass, InitVar
from os import getcwd
from os.path import isfile, join, dirname, abspath
from urllib.parse import urlparse
from yaml import safe_load
from yaml.parser import ParserError
from flask import Flask, render_template, url_for, abort
from flask_frozen import relative_url_for
from werkzeug.exceptions import HTTPException

_Opt = Mapping[str, str]
_Data = Dict[str, Any]
_YamlValue = Union[bool, int, float, str, list, dict]
T = TypeVar('T', bound=Union[_YamlValue, 'TypeChecker'])
U = TypeVar('U', bound=_YamlValue)

PWD = abspath(getcwd())
ROOT = abspath(dirname(__file__))
PROJECT = "reveal.yaml"
KEY = (join(PWD, 'localhost.crt'), join(PWD, 'localhost.key'))
app = Flask(__name__)


def load_yaml() -> _Data:
    """Load project."""
    with open(PROJECT, 'r', encoding='utf-8') as f:
        data: _Data = safe_load(f)
    for key in tuple(data):
        data[key.replace('-', '_')] = data.pop(key)
    return data


@overload
def cast_to(t: Type[List[T]], value: _YamlValue) -> List[T]:
    pass


@overload
def cast_to(t: Type[T], value: _YamlValue) -> T:
    pass


def cast_to(t, value):
    """Check value type."""
    if value is None:
        # Create an empty instance
        return t()
    elif hasattr(t, '__origin__') and t.__origin__ is list:
        # Is listed items
        t = t.__args__[0]
        if issubclass(t, TypeChecker) and is_dataclass(t):
            return t.as_list(value)
        else:
            return [cast_to(t, v) for v in value]
    elif isinstance(value, t):
        return value
    elif (
        issubclass(t, TypeChecker)
        and is_dataclass(t)
        and isinstance(value, dict)
    ):
        return t.from_dict(value)
    abort(500, f"expect type: {t}, get: {type(value)}")


def uri(path: str) -> str:
    """Handle the relative path and URIs."""
    if not path:
        return ""
    u = urlparse(path)
    if all((u.scheme, u.netloc, u.path)):
        return path
    if app.config.get('FREEZER_RELATIVE_URLS', False):
        return relative_url_for('static', filename=path)
    else:
        return url_for('static', filename=path)


def pixel(value: Union[int, str]) -> str:
    """Support pure number input of the size."""
    if isinstance(value, str):
        return value
    return f"{value}pt"


class TypeChecker(metaclass=ABCMeta):
    """Type checker function."""
    Self = TypeVar('Self', bound='TypeChecker')
    MaybeDict = Union[_Data, Self]
    MaybeList = Union[_Data, Sequence[_Data], Self, Sequence[Self]]

    @classmethod
    def from_dict(cls: Type[Self], data: MaybeDict) -> Self:
        """Generate a data class from dict object."""
        if isinstance(data, cls):
            return data
        return cls(**data or {})  # type: ignore

    @classmethod
    def as_list(cls: Type[Self], data: MaybeList) -> List[Self]:
        """Generate a list of Self from dict object."""
        if isinstance(data, cls):
            return [data]
        if not isinstance(data, Sequence):
            data = [cast(_Data, data)]
        return [cls.from_dict(d) for d in data]

    def __setattr__(self, key, value):
        super(TypeChecker, self).__setattr__(key, cast_to(
            get_type_hints(self.__class__).get(key, None), value))


@dataclass(repr=False, eq=False)
class Size(TypeChecker):
    """The block has size attributes."""
    src: str = ""
    width: str = ""
    height: str = ""

    def __post_init__(self):
        self.src = uri(self.src)
        self.width = pixel(self.width)
        self.height = pixel(self.height)


@dataclass(repr=False, eq=False)
class Img(Size):
    """Image class."""
    label: str = ""


@dataclass(repr=False, eq=False)
class Footer(Img):
    """Footer class."""
    link: str = ""


@dataclass(repr=False, eq=False)
class Fragment(TypeChecker):
    """Fragment option."""
    img: str = ""
    math: str = ""
    youtube: str = ""
    embed: str = ""


@dataclass(repr=False, eq=False)
class Slide(TypeChecker):
    """Slide class."""
    id: str = ""
    title: str = ""
    doc: str = ""
    math: str = ""
    img: List[Img] = field(default_factory=list)
    youtube: Size = field(default_factory=Size)
    embed: Size = field(default_factory=Size)
    fragment: Fragment = field(default_factory=Fragment)
    include: InitVar[str] = None

    def __post_init__(self, include):
        if include is not None:
            with open(join("templates", include), 'r') as f:
                self.doc = f.read()
        if not self.embed.width:
            self.embed.width = '1000px'
        if not self.embed.height:
            self.embed.height = '450px'


@dataclass(repr=False, eq=False)
class HSlide(Slide):
    """Root slide class."""
    sub: List[Slide] = field(default_factory=list)


@dataclass(repr=False, eq=False)
class Config(TypeChecker):
    title: str = "Untitled"
    description: str = ""
    author: str = ""
    theme: str = "serif"
    icon: str = "img/icon.png"
    outline: int = 0
    default_style: bool = True
    extra_style: str = ""
    watermark: str = ""
    watermark_size: str = ""
    history: bool = True
    transition: str = "slide"
    slide_num: str = "c/t"
    progress: bool = True
    footer: Footer = field(default_factory=Footer)
    nav: List[HSlide] = field(default_factory=list)

    def __post_init__(self):
        """Check arguments after assigned."""
        self.icon = uri(self.icon)
        self.watermark = uri(self.watermark)
        self.watermark_size = pixel(self.watermark_size)
        if self.extra_style:
            with open(join("templates", self.extra_style), 'r') as f:
                self.extra_style = f.read()
        if self.outline not in {0, 1, 2}:
            raise ValueError(f"outline level should be 0, 1 or 2, "
                             f"not {self.outline}")
        if not self.nav[1:] or self.outline == 0:
            return
        # Make an outline page
        doc = []
        for i, n in enumerate(self.nav[1:]):
            if n.title:
                doc.append(f"+ [{n.title}](#/{i + 1})")
            if self.outline < 2:
                continue
            for j, sn in enumerate(n.sub):
                if sn.title:
                    doc.append(" " * 2 + f"+ [{sn.title}](#/{i + 1}/{j + 1})")
        self.nav[0].sub.append(Slide(title="Outline", doc='\n'.join(doc)))

    @property
    def history_str(self) -> str:
        """Return a string version history option."""
        return str(self.history).lower()

    @property
    def slide_num_str(self) -> str:
        """Return a string version slide number option."""
        return str(self.slide_num).lower()


@app.route('/')
def presentation() -> str:
    """Generate the presentation."""
    try:
        config = load_yaml()
    except ParserError as e:
        abort(500, e)
    else:
        return render_slides(Config(**config))


@app.errorhandler(404)
@app.errorhandler(403)
@app.errorhandler(410)
@app.errorhandler(500)
def internal_server_error(e: HTTPException) -> str:
    """Error pages."""
    title = f"{e.code} {e.name}"
    return render_slides(
        Config(title=title, theme='night',
               nav=[HSlide(title=title, doc=f"```sh\n{e.description}\n```")]))


def render_slides(config: Config):
    """Rendered slides."""
    return render_template("presentation.html", config=config)


def init(path: str):
    """Create project."""
    from distutils.dir_util import mkpath, copy_tree
    mkpath(join(path, "templates"))
    copy_tree(join(ROOT, "static"), join(path, "static"))
    open(join(path, PROJECT), 'a').close()


def serve(ip: str):
    """Start server."""
    global PROJECT
    if not isfile(PROJECT):
        PROJECT = "reveal.yml"
    PROJECT = join(PWD, PROJECT)
    if not isfile(PROJECT):
        raise FileNotFoundError("project file 'reveal.yaml' is not found")
    if isfile(KEY[0]) and isfile(KEY[1]):
        from ssl import SSLContext, PROTOCOL_TLSv1_2
        context = SSLContext(PROTOCOL_TLSv1_2)
        context.load_cert_chain(KEY[0], KEY[1])
        app.run(host=ip, port=0, ssl_context=context)
    else:
        app.run(host=ip, port=0)
