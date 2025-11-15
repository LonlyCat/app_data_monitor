'use client'

import {
  Navbar as HeroNavbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  Button,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  User,
} from '@heroui/react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'

export function Navbar() {
  const { user, isAdmin, signOut } = useAuth()
  const router = useRouter()

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <HeroNavbar isBordered>
      <NavbarBrand>
        <Link href="/" className="font-bold text-inherit">
          📊 App Data Monitor
        </Link>
      </NavbarBrand>

      <NavbarContent className="hidden sm:flex gap-4" justify="center">
        <NavbarItem>
          <Link href="/apps" className="text-foreground">
            应用管理
          </Link>
        </NavbarItem>
        <NavbarItem>
          <Link href="/credentials" className="text-foreground">
            凭证管理
          </Link>
        </NavbarItem>
        <NavbarItem>
          <Link href="/rules" className="text-foreground">
            告警规则
          </Link>
        </NavbarItem>
        <NavbarItem>
          <Link href="/dashboard" className="text-foreground">
            数据看板
          </Link>
        </NavbarItem>
        <NavbarItem>
          <Link href="/schedules" className="text-foreground">
            任务调度
          </Link>
        </NavbarItem>
      </NavbarContent>

      <NavbarContent justify="end">
        {user ? (
          <Dropdown placement="bottom-end">
            <DropdownTrigger>
              <User
                as="button"
                avatarProps={{
                  isBordered: true,
                  color: isAdmin ? 'danger' : 'primary',
                }}
                className="transition-transform"
                description={isAdmin ? '管理员' : '用户'}
                name={user.email}
              />
            </DropdownTrigger>
            <DropdownMenu aria-label="用户操作" variant="flat">
              <DropdownItem key="profile" className="h-14 gap-2">
                <p className="font-semibold">登录为</p>
                <p className="font-semibold">{user.email}</p>
              </DropdownItem>
              <DropdownItem key="role" textValue="角色">
                角色: {isAdmin ? '🔑 管理员' : '👤 普通用户'}
              </DropdownItem>
              <DropdownItem key="logout" color="danger" onPress={handleSignOut}>
                退出登录
              </DropdownItem>
            </DropdownMenu>
          </Dropdown>
        ) : (
          <NavbarItem>
            <Button as={Link} href="/login" color="primary" variant="flat">
              登录
            </Button>
          </NavbarItem>
        )}
      </NavbarContent>
    </HeroNavbar>
  )
}
