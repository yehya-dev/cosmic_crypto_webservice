import uvicorn

uvicorn.run("webservice:app", port=8081, reload=True)
