import { create } from 'zustand'
import type { ProgressResponse } from '../types'

interface TaskState {
  currentAssignmentId: string | null
  currentTaskId: string | null
  progress: ProgressResponse | null
  setCurrentAssignment: (assignmentId: string, taskId: string) => void
  setProgress: (progress: ProgressResponse) => void
  clearCurrentAssignment: () => void
}

export const useTaskStore = create<TaskState>((set) => ({
  currentAssignmentId: null,
  currentTaskId: null,
  progress: null,

  setCurrentAssignment: (assignmentId, taskId) => {
    set({ currentAssignmentId: assignmentId, currentTaskId: taskId })
  },

  setProgress: (progress) => {
    set({ progress })
  },

  clearCurrentAssignment: () => {
    set({ currentAssignmentId: null, currentTaskId: null, progress: null })
  },
}))
