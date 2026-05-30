"""
OpenAPI norm

saglarstandart API dokumantasyonve Swagger UI. 
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# API surum
API_VERSION = "0.2.0"


def custom_openapi(app: FastAPI) -> dict:
    """
    ozel OpenAPI norm

    Args:
        app: FastAPI uygulamaornek

    Returns:
        OpenAPI normsozluk
    """

    def generate() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="Oh My Coder API",
            version=API_VERSION,
            description="""
## cokajan AI duzenlesurecyardimci

Oh My Coder dirbirguclubuyukcokajan AI duzenlesurecsistem, destek: 
- 🤖 **31 ozelendustri Agent** - planla, mimari, duzenlekod, test, incelemevb.
- 🌐 **12 ulkeuretbuyukmodel** - DeepSeek, Tongyi, Wenxinvb.
- 🔄 **akilliedebiliris akisi** - ontanimsablon + ozelakis
- 📊 **gorevgecmisizleizle** - tamyurutkayitvegeri oynat

### kimlik dogrulamayontem

var API istekgerekisteraraciligiylaasagidakiyontemkimlik dogrulama: 

1. **API Key**: icindeistekbasekle `X-API-Key`
2. **Bearer Token**: icindeistekbasekle `Authorization: Bearer <token>`

### hizoransinir

- varsayilan: 100 istek/puandakika
- yurutgorev: 10 vegonder

### hata isleme

varhatadonusstandartformat: 

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "hataaciklama",
    "details": {}
  }
}
```
            """,
            routes=app.routes,
            tags=[
                {
                    "name": "execute",
                    "description": "gorevyurutilgili API",
                },
                {
                    "name": "history",
                    "description": "gecmiskayityonet",
                },
                {
                    "name": "agents",
                    "description": "Agent durumyonet",
                },
                {
                    "name": "templates",
                    "description": "is akisisablonyonet",
                },
                {
                    "name": "plugins",
                    "description": "eklentisistemyonet",
                },
            ],
        )

        # saglar components kaydeticinde
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        # ekleguvenliktanim
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
        }

        # globalguvenlikisteriste
        openapi_schema["security"] = [{"ApiKeyAuth": []}, {"BearerAuth": []}]

        # ekleservisbilgi
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "yerelacgonderservis",
            },
            {
                "url": "https://api.ohmycoder.com",
                "description": "yaraturetservis",
            },
        ]

        # ekledisindakisimdokumantasyon
        openapi_schema["externalDocs"] = {
            "url": "https://github.com/VOBC/oh-my-coder/blob/main/docs/API.md",
            "description": "tam API dokumantasyon",
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return generate


# API yanitmodel
OPENAPI_RESPONSES = {
    "400": {
        "description": "istekparametrehata",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "eksikazgerekliisterparametre",
                        "details": {"field": "task"},
                    }
                }
            }
        },
    },
    "401": {
        "description": "kimlik dogrulamabasarisiz",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "API Key yoketki",
                    }
                }
            }
        },
    },
    "429": {
        "description": "istekdesik",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RATE_LIMIT",
                        "message": "istekasirihizoransinir",
                        "details": {"retry_after": 60},
                    }
                }
            }
        },
    },
    "500": {
        "description": "servisicindekisimhata",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "servisicindekisimhata",
                    }
                }
            }
        },
    },
}


# API ornek
OPENAPI_EXAMPLES = {
    "execute_request": {
        "summary": "yurutacgondergorev",
        "value": {
            "task": "uygulakullanicigirisislev, paketparanteztablotekildogrulamavehata isleme",
            "project_path": "/Users/user/projects/myapp",
            "model": "deepseek",
            "workflow": "build",
        },
    },
    "execute_response": {
        "summary": "gorevbaslatyanit",
        "value": {
            "status": "started",
            "task_id": "task-abc123",
            "message": "gorevbaslat, lutfenaraciligiyla SSE baglabaglanalilerlederece",
            "sse_url": "/sse/execute/task-abc123",
        },
    },
    "history_list": {
        "summary": "gecmiskayitliste",
        "value": {
            "records": [
                {
                    "task_id": "task-abc123",
                    "task": "uygulakullanicigirisislev",
                    "workflow": "build",
                    "status": "completed",
                    "started_at": "2024-01-15T10:30:00",
                    "completed_at": "2024-01-15T10:45:00",
                    "stats": {
                        "total_tokens": 15000,
                        "execution_time": 900,
                    },
                }
            ],
            "pagination": {"total": 100, "limit": 50, "offset": 0},
        },
    },
    "agent_status": {
        "summary": "Agent durum",
        "value": {
            "agents": [
                {
                    "name": "Planner",
                    "status": "idle",
                    "channel": "BUILD",
                    "level": "MEDIUM",
                    "description": "planlaacgonderplan",
                },
                {
                    "name": "Executor",
                    "status": "running",
                    "current_task": "olusturgiristablotekilkod",
                    "progress": 75,
                    "channel": "BUILD",
                    "level": "LOW",
                },
            ]
        },
    },
}
