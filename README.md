# FREEDOM-RT

Real-time personalized fashion recommendation system.

## Prerequisites

Install:

- Git
- Docker Desktop
- Node.js 20+

## 1. Clone Project

```bash
git clone <your-github-repo-url>
cd multimodal-fashion
```

## 2. Prepare Data

Make sure these files exist:

```text
dataset/
  image_feat.npy
  text_feat.npy
  saved/
    teacher_item_128.npy
    student_mlp.pth
```

The backend needs these files to compute recommendations and load the Student MLP.

## 3. Configure Backend

Create `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Update these values in `.env`:

```env
WEAVIATE_URL=https://your-cluster.weaviate.cloud
WEAVIATE_API_KEY=your_weaviate_api_key
WEAVIATE_COLLECTION=FashionItem
```

## 4. Run Backend

Start FastAPI and Redis:

```bash
docker compose up -d --build
```

Backend URL:

```text
http://localhost:8000
```

Test quickly:

```bash
curl "http://localhost:8000/api/v1/home?limit=3"
```

On Windows PowerShell:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/home?limit=3"
```

## 5. Configure Frontend

Go to frontend:

```bash
cd frontend
```

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET=your_unsigned_upload_preset
```

Cloudinary config is only required for the Admin Add Product page.

## 6. Run Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

## Useful Pages

```text
Home:   http://localhost:3000
Search: http://localhost:3000/search
Admin:  http://localhost:3000/admin/add-product
```

## Stop Project

From the project root:

```bash
docker compose down
```

## Optional Checks

Backend tests:

```bash
python -m pytest -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```
