-- 邀请奖励系统
-- 添加邀请关系表和用户邀请统计字段

-- 用户邀请关系表
CREATE TABLE user_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inviter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invitee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reward_points INTEGER NOT NULL DEFAULT 300,
    reward_applied BOOLEAN NOT NULL DEFAULT FALSE,
    reward_applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_invites_invitee UNIQUE (invitee_id)
);

CREATE INDEX idx_user_invites_inviter ON user_invites(inviter_id);
CREATE INDEX idx_user_invites_invitee ON user_invites(invitee_id);
CREATE INDEX idx_user_invites_reward_applied ON user_invites(reward_applied);

COMMENT ON TABLE user_invites IS '用户邀请关系表，记录邀请者与被邀请者的关系及奖励发放状态。';
COMMENT ON COLUMN user_invites.inviter_id IS '邀请者用户ID';
COMMENT ON COLUMN user_invites.invitee_id IS '被邀请者用户ID';
COMMENT ON COLUMN user_invites.reward_points IS '本次邀请发放的奖励积分数';
COMMENT ON COLUMN user_invites.reward_applied IS '奖励是否已发放';
COMMENT ON COLUMN user_invites.reward_applied_at IS '奖励发放时间';

-- 为用户表添加邀请统计字段
ALTER TABLE users 
  ADD COLUMN inviter_id UUID REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN successful_invite_count INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN users.inviter_id IS '邀请我的用户ID（首次注册时的邀请者）';
COMMENT ON COLUMN users.successful_invite_count IS '我成功邀请的用户数量';

CREATE INDEX idx_users_inviter ON users(inviter_id) WHERE inviter_id IS NOT NULL;

-- 创建触发器更新 updated_at
CREATE TRIGGER trg_user_invites_set_updated_at
BEFORE UPDATE ON user_invites
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
