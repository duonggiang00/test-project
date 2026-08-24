import { Roboto } from 'next/font/google';
import { create } from 'zustand';

const useStore = create(() => ({ exams: [] }));

export function BrokenComponent() {
  fetch('https://backend.example.test/exams');
  localStorage.setItem('token', 'unsafe');
  location.reload();
  const endpoint = '/exams/';
  return <div className="material-symbols-outlined bg-gradient-to-r from-red-500" style={{ color: '#ff0000' }}>{endpoint}</div>;
}
