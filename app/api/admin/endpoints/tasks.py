from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app import schemas
from app.api.admin.dependencies import get_api_task_service
from app.services.api_task_service import ApiTaskService


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[schemas.TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: Optional[int] = None,
    task_service: ApiTaskService = Depends(get_api_task_service)
) -> List[schemas.TaskResponse]:
    """Получить список задач"""
    try:
        tasks = await task_service.get_tasks(skip=skip, limit=limit)
        return [schemas.TaskResponse.from_orm(task) for task in tasks]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=schemas.TaskResponse)
async def create_task(
    task_data: schemas.TaskCreate,
    task_service: ApiTaskService = Depends(get_api_task_service)
) -> schemas.TaskResponse:
    """Создать новую задачу"""
    try:
        task = await task_service.create_task(task_data)
        return schemas.TaskResponse.from_orm(task)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}", response_model=schemas.TaskResponse)
async def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    task_service: ApiTaskService = Depends(get_api_task_service)
) -> schemas.TaskResponse:
    """Обновить задачу"""
    try:
        task = await task_service.update_task(task_id, task_update)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    task_service: ApiTaskService = Depends(get_api_task_service)
) -> dict:
    """Удалить задачу"""
    try:
        await task_service.delete_task(task_id)
        return {"message": "Task deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
