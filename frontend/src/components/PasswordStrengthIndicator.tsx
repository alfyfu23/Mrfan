'use client';

import React from 'react';
import { PasswordValidationResult, validatePasswordStrength, getPasswordStrengthDescription, getPasswordStrengthColor } from '@/utils/passwordValidator';

interface PasswordStrengthIndicatorProps {
  password: string;
  showErrors?: boolean;
  className?: string;
}

/**
 * 密码强度指示器组件
 * 显示密码强度条和错误信息
 */
export default function PasswordStrengthIndicator({ 
  password, 
  showErrors = true, 
  className = '' 
}: PasswordStrengthIndicatorProps) {
  // 如果没有密码，不显示任何内容
  if (!password) {
    return null;
  }

  const validation: PasswordValidationResult = validatePasswordStrength(password);
  const { strength, score, errors } = validation;

  return (
    <div className={`password-strength-container ${className}`}>
      <div className="password-strength-header">
        <span>密码强度：</span>
        <span 
          className="password-strength-text"
          style={{ color: getPasswordStrengthColor(strength) }}
        >
          {getPasswordStrengthDescription(strength)}
        </span>
      </div>
      
      <div className="password-strength-bar">
        <div 
          className="password-strength-fill"
          style={{ 
            width: `${score}%`,
            backgroundColor: getPasswordStrengthColor(strength)
          }}
        ></div>
      </div>
      
      {showErrors && errors.length > 0 && (
        <div className="password-errors">
          {errors.map((error, index) => (
            <div key={index} className="password-error">
              • {error}
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .password-strength-container {
          margin-top: 8px;
        }

        .password-strength-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 6px;
          font-size: 14px;
        }

        .password-strength-text {
          font-weight: 600;
        }

        .password-strength-bar {
          height: 6px;
          background-color: #f0f0f0;
          border-radius: 3px;
          overflow: hidden;
        }

        .password-strength-fill {
          height: 100%;
          transition: width 0.3s, background-color 0.3s;
        }

        .password-errors {
          margin-top: 8px;
          color: #ff4d4f;
          font-size: 12px;
        }

        .password-error {
          margin-bottom: 2px;
        }
      `}</style>
    </div>
  );
}