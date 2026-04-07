/**
 * 个人中心页
 *
 * 展示用户信息、登录/登出入口，
 * 以及学习统计和设置入口。
 */

import { View, Text, ScrollView, Image, Button, Input, type BaseEventOrig, type InputProps } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect } from 'react'
import { useConfigStore } from '../../stores/config'
import { useAuthStore } from '../../stores/auth'
import { fetchWeChatLogin, request } from '../../services/api/client'
import { getAllRecords, getVocabulary } from '../../services/storage'
import TabBar from '../../components/TabBar'
import LucideIcon from '../../components/LucideIcon'
import './index.scss'

interface ProfilePageProps {
  isSubView?: boolean
}

export default function ProfilePage({ isSubView = false }: ProfilePageProps) {
  const { purpose } = useConfigStore()
  const { isLoggedIn, userInfo, login, logout, fetchUserInfo, updateUserInfo } = useAuthStore()
  const [articleCount, setArticleCount] = useState(0)
  const [wordCount, setWordCount] = useState(0)
  const [loggingIn, setLoggingIn] = useState(false)

  useEffect(() => {
    const records = getAllRecords()
    setArticleCount(records.length)
    const vocab = getVocabulary()
    setWordCount(vocab.length)
    if (isLoggedIn) {
      fetchUserInfo()
    }
  }, [isLoggedIn])

  const handleLogin = async () => {
    setLoggingIn(true)
    try {
      const loginResult = await Taro.login()
      if (!loginResult.code) {
        Taro.showToast({ title: '微信登录失败', icon: 'none' })
        return
      }
      const res = await fetchWeChatLogin(loginResult.code)
      login(res.session_token, { user_id: res.user_id })
      Taro.showToast({ title: '登录成功', icon: 'success' })
    } catch (err) {
      console.error('[profile] login error', err)
      Taro.showToast({ title: '登录失败，请重试', icon: 'none' })
    } finally {
      setLoggingIn(false)
    }
  }

  const handleLogout = () => {
    Taro.showModal({
      title: '确认退出登录？',
      content: '退出后，您的阅读进度和生词本将停止同步到云端。',
      confirmText: '退出登录',
      confirmColor: '#ef4444',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          logout()
          Taro.showToast({ title: '已安全退出', icon: 'success' })
        }
      }
    })
  }

  const onChooseAvatar = async (e: any) => {
    const { avatarUrl } = e.detail
    // 实际项目中这里应上传到服务器，这里先模拟更新本地状态
    updateUserInfo({ avatar_url: avatarUrl })
    
    // 如果有后端 API 支持更新头像，可以在此调用
    try {
      await request({
        url: '/auth/user/update',
        method: 'POST',
        data: { avatar_url: avatarUrl }
      })
    } catch (err) {
      console.error('Update avatar failed', err)
    }
  }

  const onNicknameChange = async (e: BaseEventOrig<InputProps.InputValueEventDetail>) => {
    const nickname = e.detail.value
    updateUserInfo({ nickname })
    
    try {
      await request({
        url: '/auth/user/update',
        method: 'POST',
        data: { nickname }
      })
    } catch (err) {
      console.error('Update nickname failed', err)
    }
  }

  const purposeMap: Record<string, string> = {
    'daily': '日常阅读',
    'exam': 'CET-4 备考',
    'academic': '学术/专业'
  }

  const menuGroups = [
    {
      title: "学习管理",
      items: [
        { label: "当前模式配置", value: purposeMap[purpose] || "未设置", icon: 'settings', url: '/pages/onboarding/index', color: 'blue' },
        { label: "我的生词本", value: wordCount > 0 ? `${wordCount}词` : "暂无生词", icon: 'bookmark', color: 'yellow' },
      ]
    },
    {
      title: "关于与合规",
      items: [
        { label: "用户协议与隐私政策", icon: 'file', color: 'gray' },
        { label: "关于我们", icon: 'info', color: 'gray' },
      ]
    }
  ]

  const handleMenuClick = (item: { url?: string }) => {
    if (item.url) {
      Taro.navigateTo({ url: item.url })
    }
  }

  const displayName = userInfo?.nickname || (isLoggedIn ? `用户 ${(userInfo?.user_id || '').slice(0, 8)}` : '未登录')
  const avatarChar = isLoggedIn ? 'U' : 'M'

  return (
    <View className={`profile-page ${isSubView ? 'sub-view' : ''}`}>
      <ScrollView scrollY className='profile-scroll'>
        {!isSubView && (
          <View className='header'>
            <Text className='title'>我的</Text>
          </View>
        )}

        {/* User Card */}
        <View className='user-card'>
          <Button 
            className='avatar-btn' 
            openType={isLoggedIn ? 'chooseAvatar' : undefined}
            onChooseAvatar={isLoggedIn ? onChooseAvatar : undefined}
            onClick={!isLoggedIn ? handleLogin : undefined}
          >
            {userInfo?.avatar_url ? (
              <Image className='avatar-img' src={userInfo.avatar_url} mode='aspectFill' />
            ) : (
              <View className='avatar-text'>{avatarChar}</View>
            )}
          </Button>
          
          <View className='user-info'>
            {isLoggedIn ? (
              <Input
                className='nickname-input'
                type='nickname'
                value={userInfo?.nickname || ''}
                placeholder='设置昵称'
                maxlength={20}
                onBlur={onNicknameChange}
                onConfirm={onNicknameChange}
              />
            ) : (
              <Text className='nickname' onClick={handleLogin}>点击登录微信</Text>
            )}
            <View className='stats-row'>
              {articleCount > 0 ? (
                <>
                  <Text className='stats-label'>已读 </Text>
                  <Text className='stats-value'>{articleCount}</Text>
                  <Text className='stats-label'> 篇文章</Text>
                </>
              ) : (
                <Text className='stats-label'>暂无阅读记录</Text>
              )}
            </View>
          </View>

          {isLoggedIn && (
            <View className='logout-icon-btn' onClick={handleLogout}>
              <LucideIcon name='logOut' size={20} color='var(--text-muted)' />
            </View>
          )}
        </View>

        <View className='login-tip'>
          <Text className='tip-text'>
            {isLoggedIn ? '已登录 · 数据将同步到云端' : '登录后可同步数据到云端，跨设备查看'}
          </Text>
        </View>

        <View className='menu-list'>
          {menuGroups.map((group, gIdx) => (
            <View key={gIdx} className='menu-group'>
              <Text className='group-title'>{group.title}</Text>
              <View className='group-box'>
                {group.items.map((item, iIdx) => (
                  <View key={iIdx} className='menu-item' onClick={() => handleMenuClick(item)}>
                    <View className='item-left'>
                      <View className={`icon-box ${item.color}`}>
                        <LucideIcon name={item.icon as any} size={18} color='currentColor' />
                      </View>
                      <Text className='label'>{item.label}</Text>
                    </View>
                    <View className='item-right'>
                      {item.value && <Text className='value-tag'>{item.value}</Text>}
                      <LucideIcon name='chevronRight' size={16} color='#ccc' />
                    </View>
                  </View>
                ))}
              </View>
            </View>
          ))}
        </View>

        <View className='version-tag'>
          <Text>AI Reader v1.0.0</Text>
        </View>
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {!isSubView && <TabBar current='profile' />}
    </View>
  )
}
