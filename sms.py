# ==============================================================================
# 文件名: sms.py
# 功能: 短信验证码工具模块
# 描述: 
#   1. 生成随机验证码
#   2. 模拟发送短信（开发环境）：打印到控制台
#   3. 预留真实发送接口（生产环境）
#   4. 验证验证码正确性
#   5. 利用 Redis 存储验证码并设置过期时间
# ==============================================================================

# 模块导入
from redis import Redis
import random
import time
import re

# 函数设计
# 随机数字生成函数——6位
def random_num():
    return ''.join(random.choices('0123456789',k = 6))


# 发送验证码
"""
简单验证手机号格式
redis记录发送时间和过期时间
redis防刷限制
模拟打印
"""
def send_sms_code(phone:str, redis_client:Redis,debug_mode:bool = True)->dict:
    #验证手机号格式
    if not phone or len(phone) != 11 or not phone.isdigit():
        return {'success': False, 'message': '手机号格式不正确'}
    
    redis_key = f'sms:{phone}'

    code  = random_num()
    # 如果用户掉线或者已存有对应数据——防刷，返回0——没发送过验证码或者验证码过期
    if redis_client and redis_client.exists(redis_key):
        try:
            # 获取剩余存活时间 (TTL)，单位秒,
            ttl = redis_client.ttl(redis_key)
            if ttl > 240:
                return {
                'success': False, 
                'message': f'操作太频繁，请 {ttl-240} 秒后再试'
                }
        except Exception as e:
            print(f"[Error] Redis 检查失败: {e}")

    if debug_mode:
        # === 开发模式：打印到控制台 ===
        print("\n" + "="*40)
        print(f"📱 [模拟短信] 收件人: {phone}")
        print(f"🔐 [模拟短信] 验证码: {code}")
        print(f"⏰ [模拟短信] 有效期: 300 秒")
        print("="*40 + "\n")
        
        # 存入 Redis: setex(键, 过期秒数, 值)
        # 原子操作：同时设置值和过期时间
        # 如果存在这个用户
        if redis_client:
            try:
                #SET (设置值) + EX (设置过期时间) 的组合命令
                redis_client.setex(redis_key, 300, code)
            except Exception as e:
                print(f"[Error] Redis 写入失败: {e}")
                return {'success': False, 'message': '服务器存储故障，请稍后重试'}
        
        # 开发模式下，为了方便测试，将验证码直接返回给前端
        return {
            'success': True, 
            'message': '验证码已发送 (见控制台)', 
            'debug_code': code  # ⚠️ 生产环境严禁返回此字段
        }
        
    else:
        # === 生产模式：调用真实短信接口 ===
        try:
            # ---------------------------------------------------------
            # TODO: 在此处接入真实的短信服务商 SDK (阿里云/腾讯云/Twilio等)
            # 示例伪代码:
            # response = sms_client.send_sms(phone_numbers=[phone], template_code='SMS_123', params={'code': code})
            # if response.status != 'OK': raise Exception("发送失败")
            # ---------------------------------------------------------
            
            # 模拟真实发送延迟
            time.sleep(0.5) 
            print(f"[生产环境] 真实短信已发送至 {phone} (内容已隐藏)")
            
            # 发送成功后，必须存入 Redis
            if redis_client:
                try:
                    redis_client.setex(redis_key, 300, code)
                except Exception as e:
                    # 如果短信发了但 Redis 存失败，需要考虑回滚或记录严重错误
                    print(f"[Critical] 短信发送成功但 Redis 存储失败: {e}")
                    # 这里可以根据业务需求决定是返回成功还是失败
            
            # 生产环境绝对不返回 debug_code
            return {
                'success': True, 
                'message': '发送成功'
            }
            
        except Exception as e:
            # 捕获真实短信接口可能抛出的任何异常
            print(f"[Error] 真实短信发送失败: {e}")
            return {
                'success': False, 
                'message': '短信服务暂时不可用，请稍后重试'
            }





# 检查验证码
"""
取出redis中的验证码
对比
成功返回状态并销毁验证码
失败返回状态并销毁验证码
"""
def verify_sms_code(phone:str,input_code,redis_client:Redis):
    #验证手机号格式
    if not phone or len(phone) != 11 or not phone.isdigit():
        return {'success': False, 'message': '手机号格式不正确'}
    
    if not input_code or len(input_code) != 6 or not input_code.isdigit():
        return {'success': False, 'message': '请输入6位数字验证码'}   
    
    redis_key = f"sms:{phone}"

    if redis_client:
        try:
            stored_code = redis_client.get(redis_key)
            # Redis 返回的是 bytes，需要解码为 string (如果是 Python 3)
            if stored_code:
                stored_code = stored_code.decode('utf-8') if isinstance(stored_code, bytes) else stored_code
        except Exception as e:
            print(f"[Error] Redis 读取失败: {e}")
            return {'success': False, 'message': '服务器繁忙，请稍后重试'}
    else:
        return {'success': False, 'message': '系统配置错误：Redis 服务未连接'}

    # --- [2] 逻辑判断 ---
    
    # 情况 A: Key 不存在 (说明从未发送过，或者已经过期被 Redis 自动删除了)
    if not stored_code:
        return {
            'success': False, 
            'message': '验证码已过期或不存在，请重新获取'
        }
    
    # 情况 B: Key 存在，但代码不匹配
    if stored_code != input_code:
        # 注意：这里不删除 Key，允许用户在剩余有效期内继续尝试
        return {
            'success': False, 
            'message': '验证码错误，请重新输入'
        }
    
    # 情况 C: 验证成功！
    # 验证通过后，立即删除该 Key
    else:
        try:
            if redis_client:
                redis_client.delete(redis_key)
                print(f"[Success] 手机号 {phone} 验证通过，Key 已销毁。")
        except Exception as e:
        # 即使删除失败，只要比对成功，通常也认为验证通过
        # 但最好记录日志，因为理论上这个码还能再用一次
            print(f"[Warning] 验证成功但删除 Key 失败: {e}")

        return {
        'success': True, 
        'message': '验证成功'
        }    