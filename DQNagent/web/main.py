from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from job_runner import runner
from map_builder import build_map, list_maps

app = FastAPI(title="FlowGrid Control Panel")
ROOT = Path(__file__).resolve().parent


class MapBuildRequest(BaseModel):
    name: str = "flowgrid"
    arm_length: int = Field(500, ge=200, le=2000)
    flows: dict[str, float] | None = None


class TrainRequest(BaseModel):
    sumocfg: str = "flowgrid.sumocfg"
    episodes: int = Field(50, ge=1, le=500)
    target_update_freq: int = Field(10, ge=1, le=100)
    gui: bool = False
    gui_delay: int = Field(80, ge=0, le=500)


class CompareRequest(BaseModel):
    sumocfg: str = "flowgrid.sumocfg"
    baseline_green_seconds: float = Field(60, ge=5, le=300)
    seed: int = 42
    policy_path: str = "dqn_policy.pth"
    gui: bool = False
    gui_delay: int = Field(80, ge=0, le=500)


@app.get("/")
def read_root():
    html_path = ROOT / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/maps")
def api_list_maps():
    return {"maps": list_maps()}


@app.post("/api/maps/build")
def api_build_map(req: MapBuildRequest):
    try:
        result = build_map(req.name, req.arm_length, req.flows)
        return {"ok": True, "map": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/train")
def api_train(req: TrainRequest):
    job_id = runner.start_train(
        req.sumocfg, req.episodes, req.target_update_freq, req.gui, req.gui_delay
    )
    return {"job_id": job_id}


@app.post("/api/compare")
def api_compare(req: CompareRequest):
    job_id = runner.start_compare(
        req.sumocfg,
        req.baseline_green_seconds,
        req.seed,
        req.policy_path,
        req.gui,
        req.gui_delay,
    )
    return {"job_id": job_id}


@app.get("/api/jobs")
def api_jobs():
    jobs = runner.list_jobs()
    return {
        "jobs": [
            {
                "id": j.id,
                "kind": j.kind,
                "status": j.status,
                "progress": j.progress,
                "message": j.message,
                "result": j.result,
                "error": j.error,
            }
            for j in jobs[-20:]
        ]
    }


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "result": job.result,
        "error": job.error,
    }


@app.get("/api/live")
def api_live():
    return runner.get_live_state()


@app.get("/api/charts/{name}")
def api_chart(name: str):
    allowed = {"learning_curve.png", "comparison_bar.png"}
    if name not in allowed:
        raise HTTPException(status_code=404, detail="Chart not found")
    path = ROOT / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Chart not generated yet")
    return FileResponse(path)


@app.get("/state")
def legacy_state():
    live = runner.get_live_state()
    if live:
        return {
            "phase": live.get("phase", "—"),
            "queue_lengths": live.get("queue_lengths", {}),
            "wait_times": live.get("wait_times", {}),
            "arms": live.get("arms", {}),
            "movements": live.get("movements", {}),
        }
    return {
        "phase": "Idle",
        "queue_lengths": {"North": 0, "South": 0, "East": 0, "West": 0},
        "wait_times": {"North": 0, "South": 0, "East": 0, "West": 0},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
