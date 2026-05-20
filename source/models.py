import re
from dataclasses import dataclass, field


def _items(value):
    return value if isinstance(value, list) else []


def _text(value):
    return str(value or "")


def _code_from_text(pattern, text):
    match = re.search(pattern, _text(text))
    return match.group(0) if match else ""


@dataclass
class BasicData:
    nombre: str = ""
    codigo: str = ""
    familia: str = ""
    nivel: str = ""

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            nombre=_text(data.get("nombre")),
            codigo=_text(data.get("codigo")),
            familia=_text(data.get("familia")),
            nivel=_text(data.get("nivel")),
        )

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "codigo": self.codigo,
            "familia": self.familia,
            "nivel": self.nivel,
        }


@dataclass
class SummaryModule:
    text: str = ""
    ufs: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            text=_text(data.get("text")),
            ufs=[_text(item) for item in _items(data.get("ufs"))],
        )

    def to_dict(self):
        return {
            "text": self.text,
            "ufs": list(self.ufs),
        }


@dataclass
class EquipmentGroup:
    name: str = ""
    items: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            name=_text(data.get("name")),
            items=[_text(item) for item in _items(data.get("items"))],
        )

    def to_dict(self):
        return {
            "name": self.name,
            "items": list(self.items),
        }


@dataclass
class Bullet:
    text: str = ""
    children: list["Bullet"] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            text=_text(data.get("text")),
            children=[
                cls.from_dict(child)
                for child in _items(data.get("children"))
            ],
        )

    def to_dict(self):
        return {
            "text": self.text,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class ContentItem:
    title: str = ""
    bullets: list[Bullet] = field(default_factory=list)

    @property
    def number(self):
        match = re.match(r"^\s*(\d+)", self.title)
        return int(match.group(1)) if match else None

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            title=_text(data.get("title")),
            bullets=[
                Bullet.from_dict(bullet)
                for bullet in _items(data.get("bullets"))
            ],
        )

    def to_dict(self):
        return {
            "title": self.title,
            "bullets": [bullet.to_dict() for bullet in self.bullets],
        }


@dataclass
class Subcriterion:
    text: str = ""
    bullets: list[str] = field(default_factory=list)

    @property
    def code(self):
        return _code_from_text(r"\bCE\d+\.\d+\b", self.text)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            text=_text(data.get("text")),
            bullets=[_text(item) for item in _items(data.get("bullets"))],
        )

    def to_dict(self):
        return {
            "text": self.text,
            "bullets": list(self.bullets),
        }


@dataclass
class Criterion:
    text: str = ""
    subcriteria: list[Subcriterion] = field(default_factory=list)

    @property
    def code(self):
        return _code_from_text(r"\bC\d+\b", self.text)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            text=_text(data.get("text")),
            subcriteria=[
                Subcriterion.from_dict(subcriterion)
                for subcriterion in _items(data.get("subcriteria"))
            ],
        )

    def to_dict(self):
        return {
            "text": self.text,
            "subcriteria": [
                subcriterion.to_dict()
                for subcriterion in self.subcriteria
            ],
        }


@dataclass
class TrainingUnit:
    number: int = 0
    code: str = ""
    name: str = ""
    hours: str = ""
    criteria: list[Criterion] = field(default_factory=list)
    contents: list[ContentItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            number=int(data.get("number") or 0),
            code=_text(data.get("code")),
            name=_text(data.get("name")),
            hours=_text(data.get("hours")),
            criteria=[
                Criterion.from_dict(criterion)
                for criterion in _items(data.get("criteria"))
            ],
            contents=[
                ContentItem.from_dict(content)
                for content in _items(data.get("contents"))
            ],
        )

    def to_dict(self):
        return {
            "number": self.number,
            "code": self.code,
            "name": self.name,
            "hours": self.hours,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "contents": [content.to_dict() for content in self.contents],
        }


@dataclass
class TrainingModule:
    identifier: str = ""
    hours: str = ""
    objective: str = ""
    criteria: list[Criterion] = field(default_factory=list)
    contents: list[ContentItem] = field(default_factory=list)
    ufs: list[TrainingUnit] = field(default_factory=list)

    @property
    def code(self):
        return _code_from_text(r"\bMF\d{4}_\d\b|\bMP\d{4}\b", self.identifier)

    @property
    def name(self):
        if ":" not in self.identifier:
            return self.identifier

        return self.identifier.split(":", 1)[1].strip()

    @property
    def has_ufs(self):
        return bool(self.ufs)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            identifier=_text(data.get("identifier")),
            hours=_text(data.get("hours")),
            objective=_text(data.get("objective")),
            criteria=[
                Criterion.from_dict(criterion)
                for criterion in _items(data.get("criteria"))
            ],
            contents=[
                ContentItem.from_dict(content)
                for content in _items(data.get("contents"))
            ],
            ufs=[
                TrainingUnit.from_dict(uf)
                for uf in _items(data.get("ufs"))
            ],
        )

    def to_dict(self):
        return {
            "identifier": self.identifier,
            "hours": self.hours,
            "objective": self.objective,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "contents": [content.to_dict() for content in self.contents],
            "ufs": [uf.to_dict() for uf in self.ufs],
        }


@dataclass
class DocumentPayload:
    data: BasicData = field(default_factory=BasicData)
    modules: list[SummaryModule] = field(default_factory=list)
    spaces: list[str] = field(default_factory=list)
    equipment_groups: list[EquipmentGroup] = field(default_factory=list)
    duration_text: str = ""
    training_modules: list[TrainingModule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            data=BasicData.from_dict(data.get("data")),
            modules=[
                SummaryModule.from_dict(module)
                for module in _items(data.get("modules"))
            ],
            spaces=[_text(space) for space in _items(data.get("spaces"))],
            equipment_groups=[
                EquipmentGroup.from_dict(group)
                for group in _items(data.get("equipment_groups"))
            ],
            duration_text=_text(data.get("duration_text")),
            training_modules=[
                TrainingModule.from_dict(module)
                for module in _items(data.get("training_modules"))
            ],
        )

    def to_dict(self):
        return {
            "data": self.data.to_dict(),
            "modules": [module.to_dict() for module in self.modules],
            "spaces": list(self.spaces),
            "equipment_groups": [
                group.to_dict()
                for group in self.equipment_groups
            ],
            "duration_text": self.duration_text,
            "training_modules": [
                module.to_dict()
                for module in self.training_modules
            ],
        }
