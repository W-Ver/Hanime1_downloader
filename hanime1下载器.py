#!/usr/bin/env python3
"""
视频批量下载器 - 单线程防风控版
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import time
import re
import os
import subprocess
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import requests
from datetime import datetime
import hashlib
import webbrowser
from threading import Timer
import tkinter as tk
from tkinter import filedialog

app = Flask(__name__)
CORS(app)

# 全局变量
download_progress = {}
download_tasks = {}
download_settings = {
    'download_delay': 3,
    'download_dir': str(Path.home() / 'Downloads' / 'Videos'),
    'retry_count': 3,
    'quality_priority': ['1080p', '720p', '480p', '360p', '240p']
}

# HTML模板 - 毛玻璃UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频下载器 Pro</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --glass-bg: rgba(255, 255, 255, 0.1);
            --glass-border: rgba(255, 255, 255, 0.2);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.8);
            --shadow-xl: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            position: relative;
            overflow-x: hidden;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.05" d="M0,192L48,197.3C96,203,192,213,288,229.3C384,245,480,267,576,250.7C672,235,768,181,864,181.3C960,181,1056,235,1152,234.7C1248,235,1344,181,1392,154.7L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>') no-repeat bottom;
            background-size: cover;
            pointer-events: none;
            opacity: 0.3;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }

        .glass {
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            box-shadow: var(--shadow-xl);
        }

        .header {
            text-align: center;
            color: var(--text-primary);
            margin-bottom: 40px;
            animation: fadeInDown 0.8s ease;
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            background: linear-gradient(135deg, #fff, #e0e7ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header p {
            font-size: 1.2rem;
            color: var(--text-secondary);
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .card {
            padding: 30px;
            margin-bottom: 24px;
            animation: fadeInUp 0.8s ease;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4);
        }

        .input-group {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
        }

        .input-wrapper {
            flex: 1;
            position: relative;
        }

        .input-wrapper input {
            width: 100%;
            padding: 14px 20px;
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid transparent;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            color: #333;
        }

        .input-wrapper input:focus {
            outline: none;
            background: white;
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
        }

        .btn {
            padding: 14px 28px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
        }

        .btn-success {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }

        .btn-warning {
            background: linear-gradient(135deg, var(--warning), #d97706);
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }

        .settings-panel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
        }

        .setting-item {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .setting-label {
            color: var(--text-secondary);
            font-size: 14px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .setting-control {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .setting-control input[type="number"],
        .setting-control select {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            color: #333;
            font-size: 14px;
            flex: 1;
        }

        .folder-path {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 13px;
            font-family: monospace;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }

        .stat-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }

        .stat-item:hover {
            transform: translateY(-2px);
            background: linear-gradient(135deg, rgba(255,255,255,0.15), rgba(255,255,255,0.08));
        }

        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: 4px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .video-list {
            max-height: 600px;
            overflow-y: auto;
            padding: 12px;
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
        }

        .video-list::-webkit-scrollbar {
            width: 8px;
        }

        .video-list::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }

        .video-list::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 4px;
        }

        .video-item {
            display: flex;
            align-items: center;
            padding: 16px;
            margin-bottom: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .video-item:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(4px);
            border-color: rgba(255, 255, 255, 0.3);
        }

        .video-item.current {
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(245, 158, 11, 0.1));
            border-color: rgba(251, 191, 36, 0.5);
        }

        .video-item.same-series {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.1));
            border-color: rgba(59, 130, 246, 0.5);
        }

        .video-checkbox {
            width: 22px;
            height: 22px;
            margin-right: 16px;
            cursor: pointer;
            accent-color: var(--primary);
        }

        .video-info {
            flex: 1;
            min-width: 0;
            color: var(--text-primary);
        }

        .video-title {
            font-weight: 600;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }

        .video-url {
            font-size: 12px;
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            opacity: 0.8;
        }

        .video-meta {
            display: flex;
            gap: 12px;
            margin-top: 8px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-current {
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(245, 158, 11, 0.2));
            color: #fbbf24;
            border: 1px solid rgba(251, 191, 36, 0.4);
        }

        .badge-series {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(37, 99, 235, 0.2));
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.4);
        }

        .badge-quality {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.3), rgba(5, 150, 105, 0.2));
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }

        .progress-container {
            margin-top: 24px;
        }

        .progress-bar {
            width: 100%;
            height: 40px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            overflow: hidden;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, var(--success), #059669);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            position: relative;
            overflow: hidden;
        }

        .progress-fill::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            100% {
                left: 100%;
            }
        }

        .queue-item {
            padding: 10px 14px;
            margin-bottom: 8px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s;
        }
        
        .queue-item.downloading {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.1));
            border-color: rgba(59, 130, 246, 0.5);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }
        
        .queue-item.completed {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1));
            border-color: rgba(16, 185, 129, 0.3);
        }
        
        .queue-item.failed {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
            border-color: rgba(239, 68, 68, 0.3);
        }
        
        .queue-item.waiting {
            opacity: 0.6;
        }

        .result-item {
            padding: 14px 18px;
            margin-bottom: 10px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: slideIn 0.3s ease;
            color: var(--text-primary);
        }

        .result-success {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1));
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .result-failed {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .actions {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .status-message {
            padding: 16px 20px;
            border-radius: 10px;
            text-align: center;
            display: none;
            margin-top: 16px;
            font-weight: 500;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .status-success {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1));
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-error {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .status-info {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.1));
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .progress-label {
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .input-group {
                flex-direction: column;
            }
            
            .actions {
                flex-direction: column;
            }
            
            .actions .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 视频下载器 Pro</h1>
            <p>单线程防风控 · 智能重试 · 毛玻璃界面</p>
        </div>

        <div class="card glass">
            <div class="input-group">
                <div class="input-wrapper">
                    <input type="text" id="urlInput" placeholder="输入视频URL (格式: https://hanime1.me/watch?v=xxxxx)" autocomplete="off">
                </div>
                <button class="btn btn-primary" onclick="analyzeUrl()" id="analyzeBtn">
                    <span id="analyzeBtnText">🔍 分析视频</span>
                    <span class="loading" style="display: none;" id="analyzeLoading"></span>
                </button>
            </div>
            
            <div class="settings-panel">
                <div class="setting-item">
                    <span class="setting-label">下载间隔(秒)</span>
                    <div class="setting-control">
                        <input type="number" id="downloadDelay" min="1" max="30" value="3">
                        <span style="color: var(--text-secondary); font-size: 12px;">防风控</span>
                    </div>
                </div>
                
                <div class="setting-item">
                    <span class="setting-label">画质优先级</span>
                    <div class="setting-control">
                        <select id="qualityPriority">
                            <option value="highest">最高画质优先</option>
                            <option value="balanced">平衡模式</option>
                            <option value="fastest">最快速度</option>
                        </select>
                    </div>
                </div>
                
                <div class="setting-item">
                    <span class="setting-label">下载目录</span>
                    <div class="setting-control">
                        <div class="folder-path" id="downloadPath" title="点击更改">~/Downloads/Videos</div>
                        <button class="btn btn-warning" onclick="changeDownloadPath()" style="padding: 8px 16px; font-size: 14px;">
                            📁 更改
                        </button>
                    </div>
                </div>
                
                <div class="setting-item">
                    <span class="setting-label">失败重试</span>
                    <div class="setting-control">
                        <input type="number" id="retryCount" min="0" max="5" value="3">
                        <span style="color: var(--text-secondary); font-size: 12px;">0-5次</span>
                    </div>
                </div>
            </div>
            
            <div id="statusMessage"></div>
        </div>

        <div class="card glass" id="videoInfo" style="display: none;">
            <h2 style="color: var(--text-primary); margin-bottom: 20px; font-size: 1.5rem;">📊 视频分析结果</h2>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value" id="totalVideos">0</div>
                    <div class="stat-label">总数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="seriesVideos">0</div>
                    <div class="stat-label">系列</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="selectedVideos">0</div>
                    <div class="stat-label">已选</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="highQualityVideos">0</div>
                    <div class="stat-label">高清</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="estimatedSize">0</div>
                    <div class="stat-label">预计(GB)</div>
                </div>
            </div>

            <div class="actions">
                <button class="btn btn-primary" onclick="selectAll()">✅ 全选</button>
                <button class="btn btn-primary" onclick="selectNone()">❌ 取消全选</button>
                <button class="btn btn-primary" onclick="selectSeries()">📂 选择系列</button>
                <button class="btn btn-primary" onclick="selectHD()">🎬 选择高清</button>
                <button class="btn btn-success" onclick="startDownload()" id="downloadBtn">
                    🚀 开始下载
                </button>
            </div>

            <div class="video-list" id="videoList"></div>
        </div>

        <div class="card glass" id="downloadProgress" style="display: none;">
            <h2 style="color: var(--text-primary); margin-bottom: 20px; font-size: 1.5rem;">📥 下载进度</h2>
            
            <div class="progress-container">
                <div class="progress-label" style="margin-bottom: 8px; color: var(--text-secondary); font-size: 14px;">
                    总进度
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%">
                        <span id="progressText">0%</span>
                    </div>
                </div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 13px;">
                    <span id="progressCount">0 / 0</span>
                    <span id="progressStatus">准备中...</span>
                    <span id="remainingTime">剩余: --:--</span>
                </div>
            </div>
            
            <div class="progress-container" style="margin-top: 20px;">
                <div class="progress-label" style="margin-bottom: 8px; color: var(--text-secondary); font-size: 14px;">
                    当前文件: <span id="currentFileName" style="color: var(--text-primary);">-</span>
                </div>
                <div class="progress-bar" style="height: 30px;">
                    <div class="progress-fill" id="currentProgressFill" style="width: 0%; background: linear-gradient(135deg, #3b82f6, #2563eb);">
                        <span id="currentProgressText">0%</span>
                    </div>
                </div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 13px;">
                    <span id="downloadSpeed">速度: 0 MB/s</span>
                    <span id="downloadSize">0 MB / 0 MB</span>
                    <span id="retryInfo" style="color: var(--warning);">重试: 0/3</span>
                </div>
            </div>
            
            <div style="margin-top: 24px;">
                <h3 style="color: var(--text-primary); margin-bottom: 12px; font-size: 1.1rem;">📋 下载队列</h3>
                <div id="downloadQueue" style="max-height: 300px; overflow-y: auto;"></div>
            </div>
            
            <div id="downloadResults" style="margin-top: 24px;"></div>
        </div>
    </div>

    <script>
        let currentData = null;
        let downloadTaskId = null;
        let settings = {
            downloadDelay: 3,
            downloadPath: '~/Downloads/Videos',
            qualityPriority: 'highest',
            retryCount: 3
        };

        function loadSettings() {
            const saved = localStorage.getItem('downloadSettings');
            if (saved) {
                settings = JSON.parse(saved);
                document.getElementById('downloadDelay').value = settings.downloadDelay || 3;
                document.getElementById('qualityPriority').value = settings.qualityPriority;
                document.getElementById('downloadPath').textContent = settings.downloadPath;
                document.getElementById('retryCount').value = settings.retryCount || 3;
            }
        }

        function saveSettings() {
            settings.downloadDelay = parseInt(document.getElementById('downloadDelay').value);
            settings.qualityPriority = document.getElementById('qualityPriority').value;
            settings.retryCount = parseInt(document.getElementById('retryCount').value);
            localStorage.setItem('downloadSettings', JSON.stringify(settings));
        }

        async function analyzeUrl() {
            const url = document.getElementById('urlInput').value.trim();
            
            if (!url) {
                showMessage('请输入视频URL', 'error');
                return;
            }

            if (!/https:\\/\\/hanime1\\.me\\/watch\\?v=\\d+/.test(url)) {
                showMessage('URL格式不正确', 'error');
                return;
            }

            const analyzeBtn = document.getElementById('analyzeBtn');
            const analyzeBtnText = document.getElementById('analyzeBtnText');
            const analyzeLoading = document.getElementById('analyzeLoading');
            
            analyzeBtn.disabled = true;
            analyzeBtnText.textContent = '分析中...';
            analyzeLoading.style.display = 'inline-block';
            
            showMessage('正在静默分析视频信息...', 'info');

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        url,
                        settings: settings
                    })
                });

                if (!response.ok) {
                    throw new Error('分析失败');
                }

                const data = await response.json();
                currentData = data;
                
                displayVideoList(data);
                showMessage(`✅ 分析完成！找到 ${data.playlist.length} 个视频`, 'success');
                
                document.getElementById('videoInfo').style.display = 'block';
                updateStats();
                
            } catch (error) {
                showMessage('❌ 分析失败: ' + error.message, 'error');
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtnText.textContent = '🔍 分析视频';
                analyzeLoading.style.display = 'none';
            }
        }

        function displayVideoList(data) {
            const videoList = document.getElementById('videoList');
            
            if (!data.playlist || data.playlist.length === 0) {
                videoList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">未找到视频</div>';
                return;
            }

            let html = '';
            
            data.playlist.forEach((video, index) => {
                const classes = ['video-item'];
                if (video.is_current) classes.push('current');
                if (video.is_same_series) classes.push('same-series');
                
                const badges = [];
                if (video.is_current) badges.push('<span class="badge badge-current">当前</span>');
                if (video.is_same_series) badges.push('<span class="badge badge-series">系列</span>');
                if (video.best_quality === '1080p') badges.push('<span class="badge badge-quality">HD</span>');
                
                const size = video.estimated_size || '未知';
                
                html += `
                    <div class="${classes.join(' ')}" onclick="toggleCheckbox('${video.id}')">
                        <input type="checkbox" class="video-checkbox" 
                               id="checkbox-${video.id}"
                               data-video-id="${video.id}"
                               data-url="${video.url}"
                               data-title="${video.original_title || video.title}"
                               data-size="${video.estimated_size || 0}"
                               ${video.is_same_series ? 'checked' : ''}
                               onclick="event.stopPropagation()">
                        <div class="video-info">
                            <div class="video-title">
                                ${video.original_title || video.title}
                                ${badges.join('')}
                            </div>
                            <div class="video-url">${video.url}</div>
                            <div class="video-meta">
                                <span>📊 画质: ${video.best_quality || '未知'}</span>
                                <span>💾 大小: ${size} MB</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            videoList.innerHTML = html;
            
            document.querySelectorAll('.video-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', updateStats);
            });
        }

        function toggleCheckbox(videoId) {
            const checkbox = document.getElementById(`checkbox-${videoId}`);
            checkbox.checked = !checkbox.checked;
            updateStats();
        }

        function updateStats() {
            const total = document.querySelectorAll('.video-checkbox').length;
            const selected = document.querySelectorAll('.video-checkbox:checked').length;
            const series = document.querySelectorAll('.video-item.same-series').length;
            const highQuality = currentData ? currentData.playlist.filter(v => v.best_quality === '1080p').length : 0;
            
            let totalSize = 0;
            document.querySelectorAll('.video-checkbox:checked').forEach(cb => {
                const size = parseFloat(cb.dataset.size) || 0;
                totalSize += size;
            });
            
            document.getElementById('totalVideos').textContent = total;
            document.getElementById('seriesVideos').textContent = series;
            document.getElementById('selectedVideos').textContent = selected;
            document.getElementById('highQualityVideos').textContent = highQuality;
            document.getElementById('estimatedSize').textContent = (totalSize / 1024).toFixed(1);
        }

        function selectAll() {
            document.querySelectorAll('.video-checkbox').forEach(cb => cb.checked = true);
            updateStats();
        }

        function selectNone() {
            document.querySelectorAll('.video-checkbox').forEach(cb => cb.checked = false);
            updateStats();
        }

        function selectSeries() {
            document.querySelectorAll('.video-checkbox').forEach(cb => {
                const item = cb.closest('.video-item');
                cb.checked = item.classList.contains('same-series');
            });
            updateStats();
        }

        function selectHD() {
            document.querySelectorAll('.video-checkbox').forEach(cb => {
                cb.checked = false;
            });
            currentData.playlist.forEach(video => {
                if (video.best_quality === '1080p') {
                    const cb = document.querySelector(`#checkbox-${video.id}`);
                    if (cb) cb.checked = true;
                }
            });
            updateStats();
        }

        async function changeDownloadPath() {
            try {
                const response = await fetch('/api/select-folder', {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.path) {
                    settings.downloadPath = data.path;
                    document.getElementById('downloadPath').textContent = data.path;
                    saveSettings();
                    showMessage('✅ 下载路径已更新', 'success');
                }
            } catch (error) {
                showMessage('❌ 无法更改路径', 'error');
            }
        }

        async function startDownload() {
            const selected = document.querySelectorAll('.video-checkbox:checked');
            
            if (selected.length === 0) {
                showMessage('请至少选择一个视频', 'error');
                return;
            }

            saveSettings();

            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.disabled = true;
            downloadBtn.textContent = '⏳ 准备下载...';

            const downloads = [];
            
            for (const checkbox of selected) {
                const videoId = checkbox.dataset.videoId;
                const videoInfo = currentData.playlist.find(v => v.id === videoId);
                
                if (videoInfo) {
                    downloads.push({
                        id: videoId,
                        url: videoInfo.url,
                        title: videoInfo.original_title || videoInfo.title,
                        video_info: videoInfo
                    });
                }
            }

            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        downloads,
                        settings: settings
                    })
                });

                const data = await response.json();
                downloadTaskId = data.task_id;
                
                document.getElementById('downloadProgress').style.display = 'block';
                monitorProgress();
                
            } catch (error) {
                showMessage('❌ 启动下载失败: ' + error.message, 'error');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.textContent = '🚀 开始下载';
            }
        }

        async function monitorProgress() {
            if (!downloadTaskId) return;

            try {
                const response = await fetch(`/api/progress/${downloadTaskId}`);
                const data = await response.json();
                
                const total = data.total;
                const completed = data.completed;
                const failed = data.failed;
                const progress = Math.round((completed + failed) / total * 100);
                
                const progressFill = document.getElementById('progressFill');
                const progressText = document.getElementById('progressText');
                progressFill.style.width = progress + '%';
                progressText.textContent = progress + '%';
                
                document.getElementById('progressCount').textContent = `${completed + failed} / ${total}`;
                document.getElementById('progressStatus').textContent = data.status === 'completed' ? '✅ 完成' : '⏳ 下载中';
                document.getElementById('remainingTime').textContent = `剩余: ${data.remaining || '--:--'}`;
                
                if (data.current_file) {
                    document.getElementById('currentFileName').textContent = data.current_file.name || '-';
                    
                    const currentProgress = data.current_file.progress || 0;
                    document.getElementById('currentProgressFill').style.width = currentProgress + '%';
                    document.getElementById('currentProgressText').textContent = currentProgress + '%';
                    
                    document.getElementById('downloadSpeed').textContent = `速度: ${data.current_file.speed || '0'} MB/s`;
                    document.getElementById('downloadSize').textContent = `${data.current_file.downloaded || '0'} MB / ${data.current_file.total || '0'} MB`;
                    document.getElementById('retryInfo').textContent = `重试: ${data.current_file.retry || '0'}/${settings.retryCount}`;
                }
                
                if (data.queue) {
                    updateDownloadQueue(data.queue);
                }
                
                if (data.results && data.results.length > 0) {
                    displayResults(data.results);
                }
                
                if (data.status !== 'completed') {
                    setTimeout(() => monitorProgress(), 500);
                } else {
                    const msg = failed > 0 
                        ? `⚠️ 下载完成！成功: ${completed}, 失败: ${failed}`
                        : `✅ 全部下载成功！共 ${completed} 个文件`;
                    showMessage(msg, failed > 0 ? 'error' : 'success');
                    
                    document.getElementById('currentFileName').textContent = '-';
                    document.getElementById('currentProgressFill').style.width = '0%';
                    document.getElementById('currentProgressText').textContent = '0%';
                }
                
            } catch (error) {
                console.error('获取进度失败:', error);
                setTimeout(() => monitorProgress(), 2000);
            }
        }
        
        function updateDownloadQueue(queue) {
            const queueDiv = document.getElementById('downloadQueue');
            let html = '';
            
            queue.forEach(item => {
                const statusIcon = {
                    'waiting': '⏳',
                    'downloading': '📥',
                    'completed': '✅',
                    'failed': '❌'
                }[item.status] || '⏳';
                
                html += `
                    <div class="queue-item ${item.status}">
                        <span style="color: var(--text-primary); font-size: 14px; flex: 1;">
                            ${statusIcon} ${item.title}
                        </span>
                        <span class="queue-status">
                            ${item.status === 'downloading' ? '下载中...' : 
                              item.status === 'completed' ? '完成' :
                              item.status === 'failed' ? '失败' : '等待'}
                        </span>
                    </div>
                `;
            });
            
            queueDiv.innerHTML = html;
        }

        function displayResults(results) {
            const resultsDiv = document.getElementById('downloadResults');
            let html = '<h3 style="color: var(--text-primary); margin-bottom: 16px;">📋 下载详情</h3>';
            
            results.forEach(result => {
                const className = result.status === 'success' ? 'result-success' : 'result-failed';
                const icon = result.status === 'success' ? '✅' : '❌';
                const status = result.status === 'success' ? '成功' : '失败';
                
                html += `
                    <div class="result-item ${className}">
                        <span>${icon} ${result.title}</span>
                        <span>${status}</span>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }

        function showMessage(message, type = 'info') {
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.className = `status-message status-${type}`;
            statusMessage.textContent = message;
            statusMessage.style.display = 'block';
            
            if (type === 'success' || type === 'error') {
                setTimeout(() => {
                    statusMessage.style.display = 'none';
                }, 5000);
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            loadSettings();
            
            document.getElementById('urlInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    analyzeUrl();
                }
            });
            
            document.getElementById('downloadDelay').addEventListener('change', saveSettings);
            document.getElementById('qualityPriority').addEventListener('change', saveSettings);
            document.getElementById('retryCount').addEventListener('change', saveSettings);
        });
    </script>
</body>
</html>
'''

def sanitize_filename(filename):
    """保留原始文件名，只移除真正的非法字符"""
    if not filename:
        return "untitled"
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    filename = ''.join(char for char in filename if ord(char) >= 32)
    return filename.strip()

def get_chrome_driver():
    """创建静音的Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--mute-audio')
    chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--window-size=1920,1080')
    
    prefs = {
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    return webdriver.Chrome(options=chrome_options)

def select_best_quality(video_links, priority='highest'):
    """根据优先级选择最佳画质"""
    if not video_links:
        return None, None
    
    if priority == 'highest':
        quality_priority = ['1080p', '720p', '480p', '360p', '240p']
    elif priority == 'balanced':
        quality_priority = ['720p', '1080p', '480p', '360p', '240p']
    else:
        quality_priority = ['480p', '360p', '720p', '240p', '1080p']
    
    for quality in quality_priority:
        for link in video_links:
            if quality.lower() in link.lower():
                return link, quality
    
    return video_links[0], 'unknown'

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/select-folder', methods=['POST'])
def select_folder():
    """选择下载文件夹"""
    try:
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(
            title="选择下载目录",
            initialdir=download_settings['download_dir']
        )
        root.destroy()
        
        if folder_path:
            download_settings['download_dir'] = folder_path
            return jsonify({'path': folder_path})
        else:
            return jsonify({'path': download_settings['download_dir']})
    except:
        return jsonify({'path': download_settings['download_dir']})

@app.route('/api/analyze', methods=['POST'])
def analyze_url():
    """分析URL"""
    try:
        data = request.json
        url = data.get('url', '')
        settings = data.get('settings', {})
        
        if not re.match(r'https://hanime1\.me/watch\?v=\d+', url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        driver = get_chrome_driver()
        result = {
            'url': url,
            'title': '',
            'series_name': '',
            'playlist': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            print(f"[分析] 访问: {url}")
            driver.get(url)
            wait = WebDriverWait(driver, 20)
            time.sleep(2)
            
            current_original_title = ""
            try:
                title_element = driver.find_element(By.ID, "shareBtn-title")
                current_original_title = title_element.text.strip()
                result['title'] = current_original_title
            except:
                try:
                    result['title'] = driver.title.split(' - ')[0].strip()
                except:
                    pass
            
            series_name = ""
            if current_original_title:
                pattern = current_original_title
                pattern = re.sub(r'\[.*?\]', '', pattern)
                pattern = re.sub(r'\s*\d+\s*$', '', pattern)
                pattern = re.sub(r'\s*[一二三四五六七八九十]+\s*$', '', pattern)
                series_name = pattern.strip()
                result['series_name'] = series_name
            
            print(f"[分析] 当前标题: {current_original_title}")
            print(f"[分析] 系列名称: {series_name}")
            
            playlist_container = None
            try:
                playlist_container = driver.find_element(By.ID, "playlist-scroll")
            except:
                try:
                    playlist_container = driver.find_element(By.CSS_SELECTOR, "div.hover-video-playlist")
                except:
                    pass
            
            if playlist_container:
                link_elements = playlist_container.find_elements(By.CSS_SELECTOR, "div > a[href*='watch?v=']")
                print(f"[分析] 找到 {len(link_elements)} 个视频")
                
                for idx, link_element in enumerate(link_elements):
                    try:
                        href = link_element.get_attribute("href")
                        if not href or not re.match(r'https://hanime1\.me/watch\?v=\d+', href):
                            continue
                        
                        parent_div = link_element.find_element(By.XPATH, "..")
                        
                        video_title = ""
                        try:
                            title_elem = parent_div.find_element(By.CSS_SELECTOR, ".card-mobile-title")
                            video_title = title_elem.text.strip()
                        except:
                            inner_divs = parent_div.find_elements(By.CSS_SELECTOR, "div")
                            for div in inner_divs:
                                text = div.text.strip()
                                if text and len(text) > 2 and not re.match(r'^\d+:\d+$', text) and '次' not in text:
                                    video_title = text
                                    break
                        
                        if not video_title:
                            video_title = f"视频 {idx + 1}"
                        
                        is_current = href == url or '現正播放' in parent_div.text
                        
                        is_same_series = False
                        if series_name:
                            clean_title = re.sub(r'\[.*?\]', '', video_title).strip()
                            if series_name in clean_title or \
                               re.sub(r'\s*\d+\s*$', '', clean_title).strip() == series_name:
                                is_same_series = True
                        
                        playlist_item = {
                            'id': hashlib.md5(href.encode()).hexdigest()[:8],
                            'url': href,
                            'title': video_title,
                            'original_title': video_title,
                            'is_current': is_current,
                            'is_same_series': is_same_series,
                            'best_quality': None,
                            'estimated_size': round(300 + (idx * 50), 2)
                        }
                        
                        if is_current and current_original_title:
                            playlist_item['original_title'] = current_original_title
                        
                        result['playlist'].append(playlist_item)
                        
                    except Exception as e:
                        print(f"[错误] 处理视频 {idx}: {e}")
                        continue
            
            try:
                play_button = driver.find_element(By.CSS_SELECTOR, "div.plyr > button")
                play_button.click()
                time.sleep(3)
            except:
                pass
            
            video_urls = []
            
            try:
                video_elements = driver.find_elements(By.TAG_NAME, "video")
                for video in video_elements:
                    src = video.get_attribute("src")
                    if src:
                        video_urls.append(src)
            except:
                pass
            
            try:
                page_source = driver.page_source
                m3u8_links = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', page_source)
                video_urls.extend(m3u8_links)
                
                mp4_links = re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', page_source)
                video_urls.extend(mp4_links)
            except:
                pass
            
            video_urls = list(set(video_urls))
            
            quality_priority = settings.get('qualityPriority', 'highest')
            best_link, best_quality = select_best_quality(video_urls, quality_priority)
            
            for item in result['playlist']:
                if item['is_current']:
                    item['video_links'] = video_urls
                    item['best_quality'] = best_quality
                    item['best_link'] = best_link
                    if best_quality == '1080p':
                        item['estimated_size'] = 800
                    elif best_quality == '720p':
                        item['estimated_size'] = 500
                    else:
                        item['estimated_size'] = 300
                    break
            
            result['playlist'].sort(key=lambda x: (not x['is_same_series'], not x['is_current']))
            
        finally:
            driver.quit()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[错误] 分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def start_download():
    """启动单线程顺序下载"""
    try:
        data = request.json
        downloads = data.get('downloads', [])
        settings = data.get('settings', {})
        
        if not downloads:
            return jsonify({'error': 'No videos to download'}), 400
        
        download_settings['download_delay'] = settings.get('downloadDelay', 3)
        download_settings['retry_count'] = settings.get('retryCount', 3)
        download_settings['download_dir'] = settings.get('downloadPath', download_settings['download_dir'])
        
        task_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
        download_progress[task_id] = {
            'total': len(downloads),
            'completed': 0,
            'failed': 0,
            'current': '',
            'status': 'processing',
            'results': [],
            'queue': [],
            'current_file': None,
            'remaining': '--:--'
        }
        
        for item in downloads:
            download_progress[task_id]['queue'].append({
                'title': item.get('title', ''),
                'status': 'waiting'
            })
        
        thread = threading.Thread(
            target=process_downloads_sequential,
            args=(task_id, downloads, settings)
        )
        thread.start()
        download_tasks[task_id] = thread
        
        return jsonify({'task_id': task_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fetch_video_details(url):
    """获取视频详细信息"""
    driver = get_chrome_driver()
    try:
        driver.get(url)
        time.sleep(2)
        
        original_title = ""
        try:
            title_element = driver.find_element(By.ID, "shareBtn-title")
            original_title = title_element.text.strip()
        except:
            try:
                original_title = driver.title.split(' - ')[0].strip()
            except:
                pass
        
        try:
            play_button = driver.find_element(By.CSS_SELECTOR, "div.plyr > button")
            play_button.click()
            time.sleep(3)
        except:
            pass
        
        video_urls = []
        
        try:
            video_elements = driver.find_elements(By.TAG_NAME, "video")
            for video in video_elements:
                src = video.get_attribute("src")
                if src:
                    video_urls.append(src)
        except:
            pass
        
        try:
            page_source = driver.page_source
            m3u8_links = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', page_source)
            video_urls.extend(m3u8_links)
            
            mp4_links = re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', page_source)
            video_urls.extend(mp4_links)
        except:
            pass
        
        video_urls = list(set(video_urls))
        best_link, best_quality = select_best_quality(video_urls)
        
        return {
            'original_title': original_title,
            'best_link': best_link,
            'best_quality': best_quality,
            'all_links': video_urls
        }
        
    finally:
        driver.quit()

def download_with_retry(url, output_path, max_retries=3):
    """带重试机制的下载"""
    for attempt in range(max_retries):
        try:
            print(f"[下载] 尝试 {attempt + 1}/{max_retries}: {output_path.name}")
            
            if '.m3u8' in url:
                success = download_with_ffmpeg(url, str(output_path))
            else:
                success = download_with_requests(url, str(output_path))
            
            if success and output_path.exists():
                print(f"[成功] 下载完成: {output_path.name}")
                return True
            
            if attempt < max_retries - 1:
                print(f"[重试] 等待5秒后重试...")
                time.sleep(5)
                
        except Exception as e:
            print(f"[错误] 下载失败 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    
    print(f"[失败] 下载失败，已重试 {max_retries} 次")
    return False

def process_downloads_sequential(task_id, download_list, settings):
    """单线程顺序处理下载"""
    download_dir = Path(settings.get('downloadPath', download_settings['download_dir']))
    download_dir.mkdir(parents=True, exist_ok=True)
    
    delay = settings.get('downloadDelay', 3)
    retry_count = settings.get('retryCount', 3)
    
    print(f"[下载] 开始顺序下载，间隔 {delay} 秒")
    print(f"[下载] 保存到: {download_dir}")
    
    start_time = time.time()
    
    for index, item in enumerate(download_list):
        try:
            download_progress[task_id]['queue'][index]['status'] = 'downloading'
            
            video_info = item.get('video_info', {})
            original_title = video_info.get('original_title', item.get('title', ''))
            
            download_progress[task_id]['current'] = original_title
            download_progress[task_id]['current_file'] = {
                'name': original_title,
                'progress': 0,
                'speed': '0',
                'downloaded': '0',
                'total': '0',
                'retry': 0
            }
            
            print(f"\n[{index + 1}/{len(download_list)}] 处理: {original_title}")
            
            best_link = video_info.get('best_link')
            if not best_link:
                print(f"[获取] 正在获取视频详情...")
                details = fetch_video_details(item['url'])
                original_title = details['original_title'] or original_title
                best_link = details['best_link']
            
            if not best_link:
                raise Exception("无法获取视频链接")
            
            filename = sanitize_filename(original_title)
            ext = '.mp4'
            output_path = download_dir / f"{filename}{ext}"
            
            print(f"[保存] {output_path}")
            
            success = False
            for retry in range(retry_count):
                download_progress[task_id]['current_file']['retry'] = retry
                
                if retry > 0:
                    print(f"[重试] 第 {retry}/{retry_count} 次重试")
                    time.sleep(3)
                
                success = download_with_retry(best_link, output_path, 1)
                if success:
                    break
            
            if success:
                download_progress[task_id]['completed'] += 1
                download_progress[task_id]['queue'][index]['status'] = 'completed'
                download_progress[task_id]['results'].append({
                    'title': original_title,
                    'status': 'success',
                    'filename': output_path.name
                })
                print(f"[✓] 成功: {original_title}")
            else:
                download_progress[task_id]['failed'] += 1
                download_progress[task_id]['queue'][index]['status'] = 'failed'
                download_progress[task_id]['results'].append({
                    'title': original_title,
                    'status': 'failed',
                    'error': f'Failed after {retry_count} retries'
                })
                print(f"[✗] 失败: {original_title}")
            
            elapsed = time.time() - start_time
            completed = download_progress[task_id]['completed'] + download_progress[task_id]['failed']
            if completed > 0:
                avg_time = elapsed / completed
                remaining = (len(download_list) - completed) * avg_time
                download_progress[task_id]['remaining'] = format_time(remaining)
            
            if index < len(download_list) - 1:
                print(f"[等待] 防风控延迟 {delay} 秒...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"[错误] 处理失败: {e}")
            download_progress[task_id]['failed'] += 1
            download_progress[task_id]['queue'][index]['status'] = 'failed'
            download_progress[task_id]['results'].append({
                'title': item.get('title', 'Unknown'),
                'status': 'failed',
                'error': str(e)
            })
    
    download_progress[task_id]['status'] = 'completed'
    download_progress[task_id]['current'] = ''
    download_progress[task_id]['current_file'] = None
    print(f"\n[完成] 全部下载完成！成功: {download_progress[task_id]['completed']}, 失败: {download_progress[task_id]['failed']}")

def format_time(seconds):
    """格式化时间"""
    if seconds < 0 or seconds > 86400:
        return "--:--"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def download_with_ffmpeg(url, output_path):
    """使用ffmpeg下载（静音）"""
    try:
        cmd = [
            'ffmpeg',
            '-i', url,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-loglevel', 'quiet',
            '-stats',
            '-y',
            str(output_path)
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return process.returncode == 0 and Path(output_path).exists()
        
    except subprocess.TimeoutExpired:
        print(f"[错误] ffmpeg超时")
        return False
    except FileNotFoundError:
        print("[错误] ffmpeg未安装，请先安装ffmpeg")
        return False
    except Exception as e:
        print(f"[错误] ffmpeg下载失败: {e}")
        return False

def download_with_requests(url, output_path):
    """使用requests下载（带进度）"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://hanime1.me/',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        
        session.close()
        return Path(output_path).exists()
        
    except requests.exceptions.Timeout:
        print(f"[错误] 下载超时")
        return False
    except Exception as e:
        print(f"[错误] requests下载失败: {e}")
        return False

@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """获取下载进度"""
    if task_id in download_progress:
        return jsonify(download_progress[task_id])
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取当前设置"""
    return jsonify(download_settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """更新设置"""
    try:
        data = request.json
        download_settings.update(data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def open_browser():
    """自动打开浏览器"""
    time.sleep(1)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    default_dir = Path.home() / 'Downloads' / 'Videos'
    default_dir.mkdir(parents=True, exist_ok=True)
    download_settings['download_dir'] = str(default_dir)
    
    print("=" * 70)
    print(" " * 20 + "🎬 视频下载器 Pro")
    print("=" * 70)
    print("✨ 特性:")
    print("  • 毛玻璃UI界面，极致视觉体验")
    print("  • 单线程顺序下载，防止风控")
    print("  • 自动重试机制，最多重试3次")
    print("  • 静音爬取，后台悄无声息")
    print("  • 保留原始文件名")
    print("  • 自定义下载间隔和目录")
    print("-" * 70)
    print(f"📁 默认下载目录: {download_settings['download_dir']}")
    print(f"⏱️ 默认下载间隔: {download_settings['download_delay']} 秒")
    print(f"🔄 默认重试次数: {download_settings['retry_count']} 次")
    print("-" * 70)
    print("🌐 服务器地址: http://localhost:5000")
    print("📌 按 Ctrl+C 停止服务器")
    print("=" * 70)
    
    Timer(1.0, open_browser).start()
    
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)