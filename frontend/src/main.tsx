import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import 'dayjs/locale/zh-cn'
import dayjs from 'dayjs'
import { AuthProvider } from './auth/AuthContext'
import AppRoutes from './App'
import './index.css'

dayjs.locale('zh-cn')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1f5fa8',
          borderRadius: 6,
        },
      }}
    >
      <AntdApp>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
