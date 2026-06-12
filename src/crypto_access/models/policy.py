"""
AccessPolicy Model (BM7)
Stores ABAC policy rules in database for PyCasbin
"""

from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel


class AccessPolicy(BaseModel):
    """
    Access Policy for ABAC (BM7)
    Defines who can access what resources under which conditions
    """
    EFFECT_CHOICES = [
        ('allow', 'Allow'),
        ('deny', 'Deny'),
    ]
    
    RESOURCE_CHOICES = [
        ('document', 'Document'),
        ('key', 'Key Revocation List'),
        ('user', 'User Management'),
        ('policy', 'Policy Management'),
        ('attribute', 'Attribute Management'),
        ('audit', 'Audit Logs'),
        ('*', 'All Resources'),
    ]
    
    ACTION_CHOICES = [
        ('read', 'Read'),
        ('write', 'Write/Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('encrypt', 'Encrypt'),
        ('decrypt', 'Decrypt'),
        ('manage', 'Full Management'),
        ('*', 'All Actions'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Policy name for identification"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this policy does"
    )
    
    # Subject condition (ABAC expression)
    # Examples:
    # - "r.sub.user_type == 'admin'"
    # - "r.sub.department == 'it' && r.sub.clearance_level >= 'secret'"
    # - "r.sub.role in ['manager', 'director']"
    subject_condition = models.TextField(
        help_text="ABAC condition expression using r.sub attributes. Example: r.sub.department == 'it'"
    )
    
    cpabe_policy = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Equivalent CP-ABE policy string. Example: (department:it and clearance_level:secret)"
    )
    
    # Resource and Action
    resource = models.CharField(
        max_length=255,
        help_text="Resource this policy applies to"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Action this policy permits/denies"
    )
    
    # Effect
    effect = models.CharField(
        max_length=10,
        choices=EFFECT_CHOICES,
        default='allow',
        help_text="Whether to allow or deny this access"
    )
    
    # Priority (lower = higher priority)
    priority = models.IntegerField(
        default=100,
        help_text="Policy priority (lower number = higher priority)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this policy is active"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_policies',
        help_text="Admin who created this policy"
    )
    
    def __str__(self):
        return f"{self.name}: {self.subject_condition} -> {self.resource}/{self.action} ({self.effect})"
    
    def to_casbin_policy(self):
        """Convert to Casbin policy format: [sub_rule, obj, act, eft]"""
        return [self.subject_condition, self.resource, self.action, self.effect]
        
    def _generate_cpabe_policy(self):
        """Auto-generate CP-ABE policy from ABAC subject_condition"""
        if not self.subject_condition:
            return ""
            
        import ast
        
        expr = self.subject_condition.replace('&&', ' and ').replace('||', ' or ')
        try:
            tree = ast.parse(expr, mode='eval')
        except SyntaxError:
            return ""
            
        def _build_rabe(node):
            if isinstance(node, ast.BoolOp):
                op_str = 'and' if isinstance(node.op, ast.And) else 'or'
                res = _build_rabe(node.values[0])
                for child in node.values[1:]:
                    res = f"({res} {op_str} {_build_rabe(child)})"
                return res
            elif isinstance(node, ast.Compare):
                attr_node = node.left
                if isinstance(attr_node, ast.Attribute):
                    attr = attr_node.attr
                else:
                    attr = attr_node.id
                attr = attr.replace('r.sub.', '')
                
                op_node = node.ops[0]
                val_node = node.comparators[0]
                
                if isinstance(op_node, ast.In):
                    if hasattr(val_node, 'elts') and val_node.elts:
                        values = [v.value if isinstance(v, ast.Constant) else str(v) for v in val_node.elts]
                        res = f"{attr}:{values[0]}"
                        for v in values[1:]:
                            res = f"({res} or {attr}:{v})"
                        return res
                    return ""
                elif isinstance(op_node, ast.Eq):
                    val = val_node.value if isinstance(val_node, ast.Constant) else str(val_node)
                    return f"{attr}:{val}"
                else:
                    val = val_node.value if isinstance(val_node, ast.Constant) else str(val_node)
                    return f"{attr}:{val}"
                    
            return ""

        return _build_rabe(tree.body)

    def save(self, *args, **kwargs):
        if self.subject_condition:
            self.cpabe_policy = self._generate_cpabe_policy()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'crypto_access_policies'
        verbose_name = 'Access Policy'
        verbose_name_plural = 'Access Policies'
        ordering = ['priority', 'name']
