from setuptools import setup


readme = open('README.md', 'r').read()


# https://stackoverflow.com/questions/2058802/how-can-i-get-the-version-defined-in-setup-py-setuptools-in-my-package
main_ns = {}
with open('subscriptions/__init__.py') as f:
    exec(f.read(), main_ns)


setup(
    name=main_ns['app_name'],
    version=main_ns['__version__'],
    packages=main_ns['app_name'],
    url=main_ns['version'],
    license="MIT License",
    author='Paul Martin',
    description='Easier management of subscriptions with Stripe in Django',
    long_description=readme,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    setup_requires=['wheel'],
    install_requires=["django, djangorestframework, stripe"],
)