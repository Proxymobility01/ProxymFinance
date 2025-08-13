# authentication/forms.py

from django import forms
from django.contrib.auth.hashers import check_password

from .models import Employe, UserAgence, Agence


class LoginForm(forms.Form):
    """
    Formulaire de connexion personnalisé qui vérifie les différentes tables d'utilisateurs.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'id': 'email',
                'placeholder': 'exemple@proxym.com',
                'required': True
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'id': 'password',
                'placeholder': 'Votre mot de passe',
                'required': True
            }
        )
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'id': 'remember'
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        # Vérification dans plusieurs tables d'utilisateurs
        self.user_type = None
        self.user_data = None

        import bcrypt

        # Vérifier d'abord dans la table des employés
        try:
            employe = Employe.objects.get(email=email.strip().lower())
            print("🎯 Employé trouvé :", employe.email)

            if bcrypt.checkpw(password.encode('utf-8'), employe.password.encode('utf-8')):
                print("✅ Mot de passe valide")
                self.user_type = 'employe'
                self.user_data = employe
                return cleaned_data
            else:
                print("❌ Mot de passe invalide")

        except Employe.DoesNotExist:
            print("❌ Employé introuvable")

        except ValueError:
            # En cas d'erreur de format du hash bcrypt
            pass

        # Vérifier ensuite dans la table des utilisateurs d'agence
        try:
            user_agence = UserAgence.objects.get(email=email)
            if bcrypt.checkpw(password.encode('utf-8'), user_agence.password.encode('utf-8')):
                self.user_type = 'user_agence'
                self.user_data = user_agence
                return cleaned_data
        except UserAgence.DoesNotExist:
            pass
        except ValueError:
            pass

        # Vérifier dans la table des agences
        try:
            agence = Agence.objects.get(email=email)
            if bcrypt.checkpw(password.encode('utf-8'), agence.password.encode('utf-8')):
                self.user_type = 'agence'
                self.user_data = agence
                return cleaned_data
        except Agence.DoesNotExist:
            pass
        except ValueError:
            pass

        # Si aucun utilisateur n'est trouvé ou si le mot de passe est incorrect
        raise forms.ValidationError("Email ou mot de passe incorrect")


class ForgotPasswordForm(forms.Form):
    """
    Formulaire pour la demande de réinitialisation de mot de passe.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Votre adresse email',
                'required': True
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Vérifier si l'email existe dans une des tables utilisateurs
        if not (Employe.objects.filter(email=email).exists() or
                UserAgence.objects.filter(email=email).exists() or
                Agence.objects.filter(email=email).exists()):
            raise forms.ValidationError("Cette adresse email n'est associée à aucun compte.")

        return email


# authentication/forms.py (ajout au fichier existant)

import bcrypt


class RegistrationForm(forms.Form):
    """
    Formulaire d'enregistrement pour les nouveaux utilisateurs.
    """
    nom = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Nom',
                'required': True
            }
        )
    )
    prenom = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Prénom',
                'required': True
            }
        )
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Email',
                'required': True
            }
        )
    )
    phone = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone',
                'required': True
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Mot de passe',
                'required': True
            }
        )
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Confirmez le mot de passe',
                'required': True
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Vérifier si l'email existe déjà
        if Employe.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        if UserAgence.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        if Agence.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        # Vérifier si le téléphone existe déjà
        if Employe.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")

        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Les mots de passe ne correspondent pas.")

        return cleaned_data

    def save(self):
        """
        Enregistre l'utilisateur avec un mot de passe hashé.
        """
        nom = self.cleaned_data.get('nom')
        prenom = self.cleaned_data.get('prenom')
        email = self.cleaned_data.get('email')
        phone = self.cleaned_data.get('phone')
        password = self.cleaned_data.get('password')

        # Hasher le mot de passe avec bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Créer un nouvel employé
        employe = Employe(
            nom=nom,
            prenom=prenom,
            email=email,
            phone=phone,
            password=hashed_password
        )
        employe.save()

        return employe