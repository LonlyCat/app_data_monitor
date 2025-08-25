from django import forms
from django.core.exceptions import ValidationError
from .models import Credential
import json


class CredentialAdminForm(forms.ModelForm):
    # Apple App Store Connect 字段
    issuer_id = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '例如: 69a6de80-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
        }),
        help_text='Apple App Store Connect API的Issuer ID'
    )
    key_id = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '例如: 2X9R4HXF34'
        }),
        help_text='Apple App Store Connect API的Key ID'
    )
    private_key = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----'
        }),
        help_text='Apple App Store Connect API的私钥内容'
    )
    
    # Google Play Console 字段
    service_account_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'placeholder': '例如: service-account@project.iam.gserviceaccount.com'
        }),
        help_text='Google Play Console Service Account邮箱地址'
    )
    service_account_key = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': '粘贴Service Account JSON密钥内容'
        }),
        help_text='Google Play Console Service Account的JSON密钥'
    )
    
    class Meta:
        model = Credential
        fields = ['platform', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 如果是编辑现有实例，预填充数据
        if self.instance and self.instance.pk:
            config_data = self.instance.get_config_data()
            
            if self.instance.platform == 'ios':
                self.fields['issuer_id'].initial = config_data.get('issuer_id', '')
                self.fields['key_id'].initial = config_data.get('key_id', '')
                self.fields['private_key'].initial = config_data.get('private_key', '')
            elif self.instance.platform == 'android':
                self.fields['service_account_email'].initial = config_data.get('service_account_email', '')
                # 不显示完整的密钥，只显示提示
                if config_data.get('service_account_key'):
                    self.fields['service_account_key'].widget.attrs['placeholder'] = '已配置（重新提交以更新）'
    
    def clean(self):
        cleaned_data = super().clean()
        platform = cleaned_data.get('platform')
        
        if platform == 'ios':
            self._validate_ios_config(cleaned_data)
        elif platform == 'android':
            self._validate_android_config(cleaned_data)
        
        return cleaned_data
    
    def _validate_ios_config(self, cleaned_data):
        """验证iOS配置"""
        issuer_id = cleaned_data.get('issuer_id')
        key_id = cleaned_data.get('key_id')
        private_key = cleaned_data.get('private_key')
        
        # 如果是新建或者有新的配置数据，则验证必填字段
        if not self.instance.pk or issuer_id or key_id or private_key:
            if not issuer_id:
                raise ValidationError({'issuer_id': 'iOS平台必须提供Issuer ID'})
            if not key_id:
                raise ValidationError({'key_id': 'iOS平台必须提供Key ID'})
            if not private_key:
                raise ValidationError({'private_key': 'iOS平台必须提供Private Key'})
            
            # 验证私钥格式
            if not (private_key.strip().startswith('-----BEGIN PRIVATE KEY-----') and 
                    private_key.strip().endswith('-----END PRIVATE KEY-----')):
                raise ValidationError({
                    'private_key': '私钥格式不正确，应以"-----BEGIN PRIVATE KEY-----"开始，以"-----END PRIVATE KEY-----"结束'
                })
    
    def _validate_android_config(self, cleaned_data):
        """验证Android配置"""
        service_account_email = cleaned_data.get('service_account_email')
        service_account_key = cleaned_data.get('service_account_key')
        
        # 如果是新建或者有新的配置数据，则验证必填字段
        if not self.instance.pk or service_account_email or service_account_key:
            if not service_account_email:
                raise ValidationError({'service_account_email': 'Android平台必须提供Service Account邮箱'})
            if not service_account_key:
                raise ValidationError({'service_account_key': 'Android平台必须提供Service Account密钥'})
            
            # 验证JSON格式
            try:
                json.loads(service_account_key)
            except json.JSONDecodeError:
                raise ValidationError({'service_account_key': 'Service Account密钥必须是有效的JSON格式'})
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 构建配置数据
        config_data = {}
        
        if instance.platform == 'ios':
            config_data = {
                'issuer_id': self.cleaned_data.get('issuer_id', ''),
                'key_id': self.cleaned_data.get('key_id', ''),
                'private_key': self.cleaned_data.get('private_key', ''),
            }
        elif instance.platform == 'android':
            config_data = {
                'service_account_email': self.cleaned_data.get('service_account_email', ''),
                'service_account_key': self.cleaned_data.get('service_account_key', ''),
            }
        
        # 只有在有新数据时才更新配置
        if any(config_data.values()):
            instance.set_config_data(config_data)
        
        if commit:
            instance.save()
        
        return instance