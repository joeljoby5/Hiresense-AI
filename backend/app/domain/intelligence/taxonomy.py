from dataclasses import dataclass
import re
import unicodedata

TAXONOMY_VERSION = "technology-2026.1"

_CATALOG = {
    "languages": {
        "Python": (), "Java": (), "JavaScript": ("JS",), "TypeScript": ("TS",),
        "C++": ("CPP",), "C#": ("C Sharp",), "C": (), "Go": ("Golang",), "Rust": (),
        "Kotlin": (), "Swift": (), "Ruby": (), "PHP": (), "Scala": (), "R": (),
    },
    "frontend": {
        "React": ("React.js", "ReactJS"), "React Native": (), "Next.js": ("NextJS",),
        "Vue": ("Vue.js", "VueJS"), "Angular": (), "HTML": ("HTML5",),
        "CSS": ("CSS3",), "Tailwind CSS": ("Tailwind",), "Accessibility": ("WCAG",),
    },
    "backend": {
        "Node.js": ("NodeJS",), ".NET": ("dotnet",), "FastAPI": (), "Django": (),
        "Flask": (), "Spring Boot": (), "Express.js": ("ExpressJS",), "GraphQL": (),
        "REST": ("REST API", "RESTful API"), "gRPC": (),
    },
    "databases": {
        "SQL": (), "NoSQL": (), "PostgreSQL": ("Postgres",), "MySQL": (),
        "SQLite": (), "MongoDB": (), "Redis": (), "SQL Server": ("MSSQL",),
    },
    "cloud_and_devops": {
        "AWS": ("Amazon Web Services",), "Azure": ("Microsoft Azure",), "GCP": ("Google Cloud Platform", "Google Cloud"),
        "Docker": (), "Kubernetes": ("K8s",), "Terraform": (), "CI/CD": ("continuous integration and delivery",),
        "Git": (), "GitHub Actions": (), "Jenkins": (),
    },
    "systems_and_security": {
        "Linux": (), "Windows Server": (), "Bash": (), "PowerShell": (), "TCP/IP": (), "DNS": (),
        "Cybersecurity": ("Information Security",), "OAuth": ("OAuth 2.0", "OAuth2"), "OpenID Connect": ("OIDC",),
    },
    "data_and_ml": {
        "Machine Learning": ("ML",), "Natural Language Processing": ("NLP",), "scikit-learn": ("sklearn",),
        "NumPy": (), "pandas": (), "PyTorch": (), "TensorFlow": (), "Tableau": (), "Power BI": (),
        "Data Visualization": ("Data Visualisation",), "Statistics": (),
    },
    "testing": {
        "Unit Testing": (), "Integration Testing": (), "Playwright": (), "Pytest": (), "Jest": (), "Selenium": (),
    },
    "professional": {
        "Technical Writing": (), "Stakeholder Management": (), "Project Management": (), "Communication": (),
        "Team Leadership": (),
    },
}


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Mention:
    skill: Skill
    start: int
    end: int


_IDS = {"C++": "cpp", "C#": "csharp", ".NET": "dotnet", "CI/CD": "ci-cd", "TCP/IP": "tcp-ip"}
SKILLS = tuple(Skill(_IDS.get(name, re.sub(r"[ .]+", "-", name.casefold())), name, category, aliases)
               for category, values in _CATALOG.items() for name, aliases in values.items())
_BY_ALIAS = {alias.casefold(): skill for skill in SKILLS for alias in (skill.name, *skill.aliases)}
_ALIASES = "|".join(re.escape(alias) for alias in sorted(_BY_ALIAS, key=lambda value: (-len(value), value)))
_MATCH = re.compile(r"(?<![\w.+#])(?:" + _ALIASES + r")(?![\w+#]|\.[A-Za-z])", re.IGNORECASE)


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def find_skills(value: str) -> list[Mention]:
    normalized = normalize(value)
    mentions = []
    for match in _MATCH.finditer(normalized):
        display = match.group()
        skill = _BY_ALIAS.get(display.casefold())
        if skill is None:
            continue
        if display.casefold() in {"c", "r", "go", "ts", "js"} and display not in {"C", "R", "Go", "TS", "JS"}:
            continue
        if display == "Go" and re.match(r"\s+(?:to|ahead|back|home|for)\b", normalized[match.end():], re.IGNORECASE):
            continue
        if display in {"C", "R"} and normalized != display and not re.search(
            r"\b(?:programming|languages?|embedded|experience|proficiency|skills?|using|developer)\b|,|\bor\b",
            normalized, re.IGNORECASE,
        ):
            continue
        mentions.append(Mention(skill, match.start(), match.end()))
    return mentions
