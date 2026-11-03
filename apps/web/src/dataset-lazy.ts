import { lazy } from 'react'

// The prompt library and zip writer load only when a dataset panel opens.
export const DatasetRunConfig = lazy(() => import('./DatasetRun').then(module => ({ default: module.DatasetRunConfig })))
export const DatasetExportPanel = lazy(() => import('./DatasetRun').then(module => ({ default: module.DatasetExportPanel })))
export const ReviewGrid = lazy(() => import('./ReviewGrid').then(module => ({ default: module.ReviewGrid })))
